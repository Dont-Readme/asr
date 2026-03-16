# ARCHITECTURE — asr-meeting-pipeline

## 1. Goals / Non-goals
Goals
- 서버에서 CLI 한 번으로 end-to-end 처리
- 단계별 산출물 저장으로 디버깅 용이성 확보
- stage 경계와 DB repo를 분리해 확장 지점 명확화
- mock 모드와 production 모드를 모두 지원해 초기 개발 속도 확보

Non-goals
- 프론트/UI 구현
- 실시간 스트리밍 처리
- 멀티테넌시/권한/과금

## 2. 전체 구조
```text
run_pipeline.py
  -> AppConfig 로드
  -> JobContext 생성
  -> Orchestrator
     -> preprocess
     -> asr (.env의 adapter command)
     -> align (.env의 adapter command)
     -> diarize (.env의 adapter command)
     -> merge
     -> summarize
     -> export
     -> SQLite repo 갱신
```

## 3. 컴포넌트 책임
- CLI: 입력 인자 파싱, 설정 override, job 생성
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
- 요약은 `vllm_generate`와 `mock` 두 provider를 지원한다.

## 6. 에러 처리
- stage 내부 오류는 `StageError`로 래핑한다.
- orchestrator는 실패 stage와 메시지를 SQLite와 로그에 기록한다.
- 민감정보와 전사 전체 원문은 로그에 남기지 않는다.

## 7. 테스트 전략
- `test_preprocess.py`: ffmpeg command 조합 검증
- `test_merge_policy.py`: overlap 기반 speaker 매핑 검증
- `test_vllm_client.py`: `/generate` 응답 파싱 검증

## 8. 향후 교체 지점
- `src/adapters/qwen_asr.py`
- `src/adapters/qwen_align.py`
- `src/adapters/pyannote_diarize.py`
- `src/db/repo.py`의 SQLite 구현체
