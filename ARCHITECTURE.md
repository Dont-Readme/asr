# ARCHITECTURE — asr-meeting-pipeline

## 1. Goals / Non-goals
Goals
- 서버에서 CLI 한 번으로 end-to-end 처리
- 기능별 독립 실행과 추후 API 노출이 가능하도록 서비스 계층 확보
- 단계별 산출물 저장으로 디버깅 용이성 확보
- stage 경계와 DB repo를 분리해 확장 지점 명확화
- mock 모드와 production 모드를 모두 지원해 초기 개발 속도 확보

Non-goals
- 프론트/UI 구현
- 실시간 스트리밍 처리
- 멀티테넌시/권한/과금

## 2. 전체 구조
```text
uv / CLI / FastAPI
  -> src/bootstrap.py (AppConfig 로드 + JobContext 생성)
  -> src/cli/*
  -> src/api/app.py
  -> src/services/*
     -> transcription (preprocess + asr + align)
     -> diarization
     -> summarization
     -> pipeline
  -> src/pipeline/orchestrator.py
     -> preprocess
     -> asr (.env의 adapter command)
     -> align (.env의 adapter command)
     -> diarize (.env의 adapter command)
     -> merge
     -> summarize
     -> export
  -> SQLite repo 갱신

Validated runtime topology (current server example; GPU assignment may change by environment)
  -> GPU 0: /root/project/vllm/run_120.sh
     -> vllm 0.15.0
     -> gpt-oss-120b
     -> port 8120
  -> GPU 1: asr pipeline
     -> preprocess (CPU/ffmpeg)
     -> asr / align / diarize
```

## 3. 컴포넌트 책임
- Bootstrap: 설정 로드, job context 생성, 공통 진입점 초기화
- CLI: 기능별 입력 인자 파싱과 서비스 호출
- API: FastAPI endpoint와 HTTP 입출력
- Services: 기능 경계 단위 orchestration
- Scripts: 반복 운영 작업(cleanup 등) 자동화
- Orchestrator: stage 순서, 상태전이, 실패 처리
- Stages: 파일 I/O 계약 유지
- Adapters: 실제 모델 추론 코드(Qwen3-ASR / Qwen3-ForcedAligner / pyannote)
- Clients: 외부 서비스 호출 캡슐화
- DB Repo: job/segment/summary/artifact 영속화
- Utils: ffmpeg, 로깅, 경로, 시간 포맷

## 4. 데이터 흐름
1. 입력 오디오를 `work/<job_id>/audio_16k_mono.wav`로 변환
2. ASR 결과를 `work/<job_id>/asr.json`으로 기록
3. Align 결과를 `work/<job_id>/align.json`으로 기록
4. Diarization 결과를 `work/<job_id>/diarization.json`, `diarization.rttm`으로 기록
5. Merge 결과를 `output/<job_id>/transcript_diarized.json`으로 기록
6. Summary 결과를 `output/<job_id>/summary.json`으로 기록
7. Export 결과를 `output/<job_id>/meeting_notes.txt`로 기록
8. SQLite에 상태/세그먼트/산출물 기록

## 5. Bootstrap 결정
- `PIPELINE_MODE=mock`일 때는 로컬 smoke test 가능한 더미 결과를 생성한다.
- production 모드에서는 `src/adapters/*`를 외부 커맨드로 호출한다.
- ASR adapter는 align 단계 호환성을 위해 기본 chunk 길이를 180초로 제한한다.
- 요약은 `vllm_generate`, `vllm_openai_chat`, `mock` provider를 지원한다.
- 기능별 CLI와 FastAPI는 동일한 서비스 계층을 재사용한다.
- 현재 검증된 운영 경로는 `vllm_generate + /v1/chat/completions + gpt-oss-120b` 조합이다.

## 6. 에러 처리
- stage 내부 오류는 `StageError`로 래핑한다.
- orchestrator는 실패 stage와 메시지를 SQLite와 로그에 기록한다.
- 기능별 서비스도 최소한의 `RUNNING/DONE/FAILED` 상태전이를 SQLite에 남긴다.
- 민감정보와 전사 전체 원문은 로그에 남기지 않는다.
- summarize는 외부 `vllm` 서버 준비 전에는 `Connection refused`가 날 수 있으므로 운영 절차에서 readiness 확인이 필요하다.

## 7. 테스트 전략
- `test_preprocess.py`: ffmpeg command 조합 검증
- `test_merge_policy.py`: overlap 기반 speaker 매핑 검증
- `test_vllm_client.py`: `/generate` 및 OpenAI chat 응답 파싱 검증
- `test_feature_services.py`: 기능별 서비스(mock) 실행 검증

## 8. 향후 교체 지점
- `src/adapters/qwen_asr.py`
- `src/adapters/qwen_align.py`
- `src/adapters/pyannote_diarize.py`
- `src/db/repo.py`의 SQLite 구현체
