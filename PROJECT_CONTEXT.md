# PROJECT_CONTEXT — asr-meeting-pipeline

## 1. 한 줄 요약
서버에서 회의 음성 파일을 전사, 화자 분리, 요약해 txt 회의록을 만드는 `uv` 기반 프로젝트이며, 현재는 `CLI`, `orchestration API`, `feature API` 구조로 정리되어 있다.

## 2. MVP 목표
- 음성 입력용 전사 API 제공
- 회의록 작성용 오케스트레이션 API 제공
- 회의록용 기능 API 3개 제공: 전사, 화자 분리, 요약
- 단계별 산출물과 로그를 로컬 폴더에 저장
- SQLite로 job 상태/오류/산출물 기록

## 3. 현재 결정된 사항(Decision Log)
1. 프로젝트 패키징은 `uv + pyproject.toml`을 단일 기준으로 사용한다.
2. 기존 `run_pipeline.py`는 호환 래퍼로 유지하고, 실제 진입점은 `src/cli/*`와 `src/api/*`에 둔다.
3. 모델 동작 코드 자체는 바꾸지 않고, API 경계와 orchestration 흐름만 재구성한다.
4. `asr-api`는 orchestration/control plane 역할로 유지한다.
5. `asr-transcribe-api`, `asr-diarize-api`, `asr-summarize-api`는 feature API 역할로 둔다.
6. `voice input`용 전사는 `ASR-only`, `meeting note`용 전사는 `ASR+align`으로 분리한다.
7. feature API public contract는 웹 연동을 위해 `upload`와 `server path` 입력을 둘 다 지원한다.
8. summarize API public contract는 `diarized transcript JSON payload`를 기본으로 사용한다.
9. orchestration API는 비동기 job 방식으로 `job_id`를 즉시 반환하고, 상태 조회는 polling으로 처리한다.
10. orchestration API는 feature API를 HTTP로 순차 호출하고, `merge`와 `export`는 내부에서 수행한다.
11. orchestration API는 여러 job을 접수할 수 있지만, 내부 worker 기본값은 `1`이며 실제 job 실행은 queue 기반 순차 처리로 제한한다.
12. transcribe API는 `voice`와 `meeting` 경로를 같은 resident ASR runtime 위에 유지하고, 공용 실행 슬롯 1개를 공유한다.
13. transcribe API에서는 `voice` 요청이 `meeting` 요청보다 높은 우선순위를 가진다.
14. align runtime은 `meeting` 요청 중에만 로드하고, 요청 완료 후 unload해 idle VRAM을 줄인다.
15. diarize API와 summarize API 기본 동시성은 각각 `1`이다.
16. 화자 라벨은 diarization 결과의 첫 등장 순서를 기준으로 `화자 A/B/C`에 매핑한다.
17. `vllm`은 별도 서버(`/root/project/vllm`)에서 먼저 기동돼 있어야 한다.
18. 현재 검증된 서버 예시는 `GPU 0 = vLLM(gpt-oss-120b, port 8120)`, `GPU 1 = asr feature API/CLI` 이며, 실제 운영에서는 GPU 배치가 바뀔 수 있다.
19. 현재 검증된 `asr` 런타임은 `Python 3.10.12`, `uv 0.9.22`, `torch/torchaudio 2.8.0+cu126`, `pyannote.audio 4.0.4` 이다.
20. 현재 검증된 `vllm` 런타임은 `Python 3.12.12`, `vllm 0.15.0` 이며 `/v1/chat/completions` route가 응답한다.

## 4. 현재 상태 요약
- 기능별 CLI(`src/cli`) 분리 완료
- orchestration API(`src/api/app.py`) 재구성 완료
- feature API 3종(`transcribe`, `diarize`, `summarize`) 정리 완료
- resident runtime 계층(`src/runtime`) 유지
- 전사 resident API는 `voice`와 `meeting` 경로를 분리 완료
- 전사 resident API는 공용 실행 슬롯 1개 + `voice` 우선순위 큐를 사용
- align runtime은 `meeting` 요청 처리 후 unload
- summarize API는 `transcript payload -> summary payload` contract 추가 완료
- orchestration API는 feature API HTTP 호출 + local merge/export 구조로 변경 완료
- orchestration API는 queue worker 기본값 `1`로 job을 순차 실행
- `scripts/clean_runtime.sh`로 `work/`, `output/`, `logs/` 정리 가능

## 5. 다음 작업(Next Actions)
- 긴 transcript 요약 chunking 전략 추가
- feature API readiness 재시도/timeout 정책 보강
- orchestration API 인증/권한 정책 결정
- resident API 기준 idle/peak VRAM, latency 계측 자동화
- `uv lock` 생성 및 GPU 서버 표준 설치 절차 고정
- Postgres 전환 및 migration 도입
- 샘플 음성 파일 3개로 품질 튜닝

## 6. 중요한 제약/주의사항
- ffmpeg 설치가 필요하다.
- production 모드는 실제 모델 실행기 또는 외부 커맨드 설정이 필요하다.
- 토큰/키와 전사 원문 전체는 로그에 남기지 않는다.
- `vllm` 120B는 준비 시간이 길고, `8120` 포트가 실제로 열리기 전에는 summarize가 `Connection refused`로 실패할 수 있다.
- resident/feature API는 코드 수정 후 자동 반영되지 않으므로 프로세스 재시작이 필요하다.

## 7. 미결 사항(Open Questions)
- 긴 회의 요약 시 chunking 및 reduce 전략
- Postgres 전환 시 migration 도구 선택
- transcribe queue에서 `voice` 요청의 대기열/timeout 기본값을 운영에서 얼마로 둘지
