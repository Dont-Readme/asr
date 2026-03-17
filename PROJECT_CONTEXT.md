# PROJECT_CONTEXT — asr-meeting-pipeline

## 1. 한 줄 요약
서버에서 회의 음성 파일을 전사, 화자 분리, 요약하여 txt 회의록을 생성하는 `uv` 기반 파이프라인이며, 기능별 CLI와 FastAPI skeleton을 함께 제공한다.

## 2. MVP 목표
- 입력 오디오를 ffmpeg로 16kHz mono wav로 변환
- 단계별 산출물과 로그를 로컬 폴더에 저장
- overlap 정책으로 화자 포함 전사본 생성
- vLLM 기반 요약 결과 생성
- SQLite로 job 상태/오류/산출물 기록

## 3. 현재 결정된 사항(Decision Log)
1. 8단계 파이프라인 구조를 유지한다.
2. 저장소 첫 구현은 부트스트랩 스켈레톤으로 구성한다.
3. preprocess, merge, summarize client, export, SQLite repo는 실제 동작 코드로 작성한다.
4. ASR/align/diarize는 provider seam을 두고 `PIPELINE_MODE=mock`에서 smoke test 가능한 mock 출력을 제공한다.
5. production 모드에서는 `src/adapters/qwen_asr.py`, `src/adapters/qwen_align.py`, `src/adapters/pyannote_diarize.py`를 외부 커맨드로 연결한다.
6. 화자 라벨은 diarization 결과의 첫 등장 순서를 기준으로 `화자 A/B/C`에 매핑한다.
7. 프로젝트 패키징은 `uv + pyproject.toml`을 단일 기준으로 사용한다.
8. 테스트는 현재 환경 제약을 반영해 `unittest` 호환으로 작성한다.
9. ASR adapter는 align 단계 호환성을 위해 기본 chunk 길이를 180초로 제한한다.
10. CUDA 12.4 서버에서 `community-1 + pyannote.audio 4.x`가 런타임 의존성(torchcodec/torchaudio)로 불안정하면 `speaker-diarization-3.1 + pyannote.audio 3.3.2`를 fallback으로 사용한다.
11. 기능 경계는 `전사(전처리+ASR+Align)`, `화자 분리`, `요약`, `파이프라인/API`의 4개로 나눈다.
12. 기존 `run_pipeline.py`는 호환 래퍼로 유지하고, 실제 진입점은 `src/cli/*`와 `src/api/*`로 옮긴다.
13. FastAPI는 모델 로직을 직접 품지 않고 서비스 계층을 재사용하는 thin API layer로 시작한다.
14. 현재 검증된 서버 예시는 `GPU 0 = vLLM(gpt-oss-120b, port 8120)`, `GPU 1 = asr pipeline` 이며, 실제 운영에서는 서버 자원/정책에 따라 GPU 배치가 바뀔 수 있다.
15. 현재 검증된 `asr` 런타임은 `Python 3.10.12`, `uv 0.9.22`, `torch/torchaudio 2.8.0+cu126`, `pyannote.audio 4.0.4` 이다.
16. 현재 검증된 `vllm` 런타임은 `Python 3.12.12`, `vllm 0.15.0` 이며 `/v1/chat/completions` route가 응답한다.
17. VRAM 안정 측정이 필요할 때는 CLI 배치가 아니라 resident API(`asr-transcribe-api`, `asr-diarize-api`)를 사용한다.
18. 기존 `asr-api` 는 서비스 계층 thin wrapper이며 모델 상주 용도가 아니다.
19. 실제 운영에서 resident API는 model-serving plane, 기존 `asr-api` 는 orchestration/control plane 으로 보는 구성이 자연스럽다.

## 4. 현재 상태 요약
- `pyproject.toml` 추가 및 `uv` 실행 기준 반영
- 기능별 서비스 계층(`src/services`)과 CLI(`src/cli`) 분리 완료
- FastAPI skeleton(`src/api`) 추가 완료
- resident runtime 계층(`src/runtime`) 및 `asr-transcribe-api` / `asr-diarize-api` 추가 완료
- 기존 stage/orchestrator는 유지하고 상위 계층만 분리
- `scripts/clean_runtime.sh`로 `work/`, `output/`, `logs/` 런타임 산출물 정리 가능
- 서버에서 `env CUDA_VISIBLE_DEVICES=1 uv run asr-pipeline ./input/test2.m4a --meeting-title "03171354"` 성공 검증 완료
- 최신 성공 산출물 예시: `output/03171354-c7bb5a06/{transcript_diarized.json,summary.json,meeting_notes.txt}`

## 5. 다음 작업(Next Actions)
- 긴 transcript 요약 chunking 전략 추가
- resident API 기준 idle/peak VRAM, latency 계측 자동화
- resident API 결과를 orchestrator와 직결할지 결정
- vLLM readiness 대기/재시도 로직 도입 여부 결정
- `uv lock` 생성 및 GPU 서버 표준 설치 절차 고정
- FastAPI 엔드포인트의 비동기 job 처리/인증 정책 결정
- Postgres 전환 및 migration 도입
- 샘플 음성 파일 3개로 품질 튜닝

## 6. 중요한 제약/주의사항
- ffmpeg 설치가 필요하다.
- production 모드는 실제 모델 실행기 또는 외부 커맨드 설정이 필요하다.
- 토큰/키와 전사 원문 전체는 로그에 남기지 않는다.
- `vllm` 서버는 `/root/project/vllm`의 별도 환경에서 먼저 기동돼 있어야 한다.
- `vllm` 120B는 준비 시간이 길고, `8120` 포트가 실제로 열리기 전에는 summarize가 `Connection refused`로 실패할 수 있다.
- resident API는 코드 수정 후 자동 반영되지 않으므로 프로세스 재시작이 필요하다.

## 7. 미결 사항(Open Questions)
- 긴 회의 요약 시 chunking 및 reduce 전략
- Postgres 전환 시 migration 도구 선택
- FastAPI를 동기 배치형으로 유지할지, 큐 기반 비동기 job 실행으로 확장할지
