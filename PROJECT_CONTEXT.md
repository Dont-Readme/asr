# PROJECT_CONTEXT — asr-meeting-pipeline

## 1. 한 줄 요약
서버에서 회의 음성 파일을 전사, 화자 분리, 요약하여 txt 회의록을 생성하는 CLI 파이프라인.

## 2. MVP 목표
- 입력 오디오를 ffmpeg로 16kHz mono wav로 변환
- 단계별 산출물과 로그를 로컬 폴더에 저장
- overlap 정책으로 화자 포함 전사본 생성
- vLLM `/generate` 기반 요약 결과 생성
- SQLite로 job 상태/오류/산출물 기록

## 3. 현재 결정된 사항(Decision Log)
1. 8단계 파이프라인 구조를 유지한다.
2. 저장소 첫 구현은 부트스트랩 스켈레톤으로 구성한다.
3. preprocess, merge, summarize client, export, SQLite repo는 실제 동작 코드로 작성한다.
4. ASR/align/diarize는 provider seam을 두고 `PIPELINE_MODE=mock`에서 smoke test 가능한 mock 출력을 제공한다.
5. production 모드에서는 `src/adapters/qwen_asr.py`, `src/adapters/qwen_align.py`, `src/adapters/pyannote_diarize.py`를 외부 커맨드로 연결한다.
6. 화자 라벨은 diarization 결과의 첫 등장 순서를 기준으로 `화자 A/B/C`에 매핑한다.
7. `requirements.txt`는 control-plane 중심으로 유지하고, 모델 런타임은 `requirements.server.txt`와 서버별 torch 설치로 분리한다.
8. 테스트는 현재 환경 제약을 반영해 `unittest` 호환으로 작성한다.
9. ASR adapter는 align 단계 호환성을 위해 기본 chunk 길이를 180초로 제한한다.

## 4. 현재 상태 요약
- 설계 문서 기반 부트스트랩 구현 진행 중
- 코드/문서/테스트 초기 생성 단계

## 5. 다음 작업(Next Actions)
- 긴 transcript 요약 chunking 전략 추가
- Postgres 전환 및 migration 도입
- 샘플 음성 파일 3개로 품질 튜닝

## 6. 중요한 제약/주의사항
- ffmpeg 설치가 필요하다.
- production 모드는 실제 모델 실행기 또는 외부 커맨드 설정이 필요하다.
- 토큰/키와 전사 원문 전체는 로그에 남기지 않는다.

## 7. 미결 사항(Open Questions)
- Qwen3-ASR / ForcedAligner의 최종 호출 API를 Python으로 직접 묶을지, 서버 커맨드 wrapper로 둘지
- 긴 회의 요약 시 chunking 및 reduce 전략
- Postgres 전환 시 migration 도구 선택
