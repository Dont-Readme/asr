# ARCHITECTURE — asr-meeting-pipeline

## 1. Goals / Non-goals
Goals
- 음성 입력용 전사 API와 회의록 작성용 orchestration API를 분리한다
- 기능별 API를 독립 배포 가능한 경계로 정리한다
- 기존에 검증된 모델/stage 로직은 유지한다
- job 상태와 산출물을 남겨 디버깅 가능하게 한다

Non-goals
- 프론트/UI 구현
- 실시간 스트리밍 처리
- 멀티테넌시/권한/과금

## 2. 전체 구조
```text
uv / CLI / FastAPI
  -> src/cli/*
     -> asr-pipeline (배치 end-to-end)
     -> asr-transcribe / asr-diarize / asr-summarize

  -> src/api/app.py
     -> orchestration API
     -> POST /meeting-note-jobs/*
     -> GET /meeting-note-jobs/{job_id}

  -> src/api/transcribe_app.py
     -> feature API
     -> /voice-transcriptions/*
     -> /meeting-transcriptions/*

  -> src/api/diarize_app.py
     -> feature API
     -> /diarizations/*

  -> src/api/summarize_app.py
     -> feature API
     -> /summaries

  -> src/services/meeting_note_jobs.py
     -> orchestration background worker
     -> feature API HTTP 호출
     -> local merge/export

  -> src/runtime/*
     -> resident model-serving runtime
     -> transcription runtime
     -> diarization runtime

  -> src/stages/*
     -> 기존 파일 기반 stage 유지
```

Validated runtime topology (current server example; GPU assignment may change by environment)
```text
GPU 0
  -> /root/project/vllm/run_120.sh
  -> vllm 0.15.0
  -> gpt-oss-120b
  -> port 8120

GPU 1
  -> asr-transcribe-api
  -> asr-diarize-api
  -> CLI batch(asr-pipeline)
```

## 3. 컴포넌트 책임
- CLI
  - 운영자 배치 실행과 디버깅
- Orchestration API
  - 회의록 작성 job 생성
  - job 상태 조회
  - feature API 순차 호출
  - merge/export 수행
- Transcribe API
  - `voice input`용 `ASR-only`
  - `meeting note`용 `ASR+align`
- Diarize API
  - 화자 분리 수행
- Summarize API
  - diarized transcript payload를 요약 payload로 변환
  - 외부 `vLLM` 서버 호출
- Runtime
  - resident API에서 모델을 startup 시 한 번만 올리고 재사용
- Services
  - orchestration helper, persistence helper, summary generation helper
- Stages
  - 기존 파일 기반 파이프라인 계약 유지
- Clients
  - `vLLM` client
  - feature API client
- DB Repo
  - job, artifact, transcript, summary 영속화

## 4. 데이터 흐름
### A. 음성 입력
1. 웹서비스가 `transcribe API /voice-transcriptions/*` 호출
2. API가 오디오를 canonical path로 정규화
3. resident ASR runtime이 전사 수행
4. 텍스트와 ASR payload 반환

### B. 회의록 작성
1. 웹서비스가 `orchestration API /meeting-note-jobs/*` 호출
2. orchestration API가 job row와 작업 디렉토리를 생성
3. background worker가 `meeting-transcriptions` API 호출
4. background worker가 `diarizations` API 호출
5. orchestration 내부에서 `merge.run` 수행
6. background worker가 `summaries` API 호출
7. orchestration 내부에서 `export.run` 수행
8. `output/<job_id>/transcript_diarized.json`, `summary.json`, `meeting_notes.txt` 생성
9. SQLite에 상태/세그먼트/산출물 기록

## 5. Bootstrap 결정
- 기존 stage/adapters/model logic는 유지한다.
- orchestration API는 feature API를 직접 import 호출하지 않고 HTTP로 부른다.
- feature API public contract는 `upload`와 `path`를 둘 다 연다.
- summarize API public contract는 `transcript payload`를 기본으로 한다.
- resident transcription runtime은 `voice`에서는 align을 생략하고, `meeting`에서만 align을 수행한다.
- resident runtime도 기존 preprocess 동작을 맞추기 위해 ffmpeg 기반 오디오 정규화를 거친다.
- `asr-api`는 orchestration/control plane, feature API는 model-serving plane으로 둔다.

## 6. 에러 처리
- feature API 호출 실패는 `StageError(ASR|DIARIZE|SUMMARIZE)`로 래핑한다.
- orchestration worker는 실패 stage와 메시지를 SQLite와 job 로그에 기록한다.
- merge/export는 기존 stage 에러 처리 방식을 그대로 따른다.
- summarize는 외부 `vLLM` 서버 준비 전에는 `Connection refused`가 날 수 있으므로 readiness 확인이 필요하다.
- resident/feature API는 startup 단계에서 모델 로딩이 실패하면 프로세스 자체가 올라오지 않는다.

## 7. 테스트 전략
- API 계약 테스트
  - transcribe API가 voice/meeting 경로를 분리하는지
  - diarize API가 upload/path 입력을 받는지
  - summarize API가 transcript payload를 받는지
  - orchestration API가 job acceptance 응답을 주는지
- orchestration 서비스 테스트
  - fake feature client 응답으로 merge/export까지 완료되는지
- 기존 stage/unit 테스트 유지
  - preprocess
  - merge policy
  - vLLM client
  - resident runtime helper

## 8. 향후 교체 지점
- `src/adapters/qwen_asr.py`
- `src/adapters/qwen_align.py`
- `src/adapters/pyannote_diarize.py`
- `src/clients/feature_api_client.py`의 HTTP contract
- `src/db/repo.py`의 SQLite 구현체
