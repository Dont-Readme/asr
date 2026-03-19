# asr-meeting-pipeline

## 1. 한 줄 요약
회의 음성 파일을 전사, 화자 분리, 요약해 텍스트 회의록으로 만드는 서버 프로젝트이며, 현재는 `CLI`, `orchestration API`, `feature API`를 함께 제공한다.

## 2. 현재 구조 설명
- `uv run asr-pipeline`
  - 배치형 end-to-end CLI다.
  - 로컬 파일 하나를 받아 `preprocess -> asr -> align -> diarize -> merge -> summarize -> export`를 끝까지 수행한다.
- `uv run asr-api`
  - orchestration/control-plane API다.
  - `meeting note job`을 만들고, 기능 API들을 호출해 최종 회의록 산출물을 만든다.
  - job은 여러 개 접수할 수 있지만 내부 worker는 기본적으로 하나씩 순차 처리한다.
- `uv run asr-transcribe-api`
  - 전사 model-serving API다.
  - `voice input`용 `ASR-only`와 `meeting note`용 `ASR+align` 엔드포인트를 함께 제공한다.
  - 두 엔드포인트는 같은 resident ASR runtime을 공유하고, `voice`가 `meeting`보다 높은 우선순위로 실행된다.
- `uv run asr-diarize-api`
  - 화자 분리 model-serving API다.
- `uv run asr-summarize-api`
  - 요약 API다.
  - resident 모델을 들고 있지 않고, 외부 `vLLM` 서버를 감싼다.
- `run_pipeline.py`
  - 기존 배치 실행 호환 래퍼다.

상세 HTTP 계약은 [API_SPEC.md](/home/kdm_theimc/coding/asr/API_SPEC.md) 를 참고한다.

## 3. 현재 구현 범위
- `uv` 기반 단일 프로젝트 패키징(`pyproject.toml`)
- 배치 CLI: `asr-transcribe`, `asr-diarize`, `asr-summarize`, `asr-pipeline`
- orchestration API: `asr-api`
- feature API: `asr-transcribe-api`, `asr-diarize-api`, `asr-summarize-api`
- SQLite 기반 job 상태/산출물 기록
- 단계별 산출물 저장: `work/<job_id>`, `output/<job_id>`, `logs/<job_id>.log`
- production adapter: Qwen3-ASR, Qwen3-ForcedAligner, pyannote diarization, external vLLM
- `mock` 모드 유지

## 4. 빠른 시작
현재 검증된 서버 기준 절차다.

1. `asr` 프로젝트 의존성 설치

```bash
cd /root/project/asr
uv sync --python 3.10 --group transcribe --group diarize --group summarize --group api --group dev
uv pip install "torch==2.8.0" "torchaudio==2.8.0" --index-url https://download.pytorch.org/whl/cu126
cp .env.example .env
```

2. 시스템 패키지 준비

```bash
apt-get update
apt-get install -y ffmpeg
ffmpeg -version
```

3. `vLLM` 서버 준비

```bash
cd /root/project/vllm
source .venv/bin/activate
python -V
python - <<'PY'
import vllm
print(vllm.__version__)
PY
bash run_120.sh
```

4. `vLLM` 준비 완료 대기

```bash
ss -ltnp | grep 8120
tail -n 80 logs/$(ls -t logs | head -n 1)
```

성공 기준:
- `Starting vLLM API server 0 on http://0.0.0.0:8120`
- `Application startup complete`
- `ss -ltnp | grep 8120` 에서 포트가 보인다

5. 기능 API 기동

```bash
cd /root/project/asr
# 예시: transcribe는 GPU 1, diarize는 GPU 0
CUDA_DEVICE=1 bash scripts/run_transcribe_api.sh
CUDA_DEVICE=0 bash scripts/run_diarize_api.sh
bash scripts/run_summarize_api.sh
```

6. orchestration API 기동

기본 포트는 `8080`이다. 다만 실제 서버에서는 `8080`이 다른 프로세스에 의해 점유될 수 있으므로, 아래 예시는 `8090`을 사용한다.

```bash
cd /root/project/asr
ORCH_PORT=8090
uv run asr-api --host 0.0.0.0 --port "$ORCH_PORT"
```

7. 회의록 job 생성

```bash
curl -s http://127.0.0.1:${ORCH_PORT:-8090}/meeting-note-jobs/by-path \
  -H 'Content-Type: application/json' \
  -d '{"audio_path":"./input/test2.m4a","meeting_title":"03171354"}'
```

8. job 상태 조회

```bash
curl -s http://127.0.0.1:${ORCH_PORT:-8090}/meeting-note-jobs/<job_id>
```

배치 CLI는 여전히 유지된다.

```bash
cd /root/project/asr
env CUDA_VISIBLE_DEVICES=1 uv run asr-pipeline ./input/test2.m4a --meeting-title "03171354"
```

## 5. API 계약
### 5-1. 전사 API
- `POST /voice-transcriptions/by-path`
- `POST /voice-transcriptions/upload`
- `POST /meeting-transcriptions/by-path`
- `POST /meeting-transcriptions/upload`

설명:
- `voice-transcriptions`는 `ASR-only`다.
- `meeting-transcriptions`는 `ASR + align`을 반환한다.
- 업로드와 서버 경로 입력을 둘 다 지원하지만, 내부에서는 하나의 파일 경로 흐름으로 정규화한다.
- transcribe API는 공용 실행 슬롯 1개를 쓰며, `voice` 요청이 먼저 실행된다.
- `align`은 `meeting-transcriptions` 요청 시에만 로드되고 요청이 끝나면 unload된다.

호출 예시:

```bash
curl -s http://127.0.0.1:8091/voice-transcriptions/by-path \
  -H 'Content-Type: application/json' \
  -d '{"audio_path":"./input/test2.m4a","language":"ko"}'
```

```bash
curl -s http://127.0.0.1:8091/meeting-transcriptions/by-path \
  -H 'Content-Type: application/json' \
  -d '{"audio_path":"./input/test2.m4a","language":"ko"}'
```

### 5-2. 화자 분리 API
- `POST /diarizations/by-path`
- `POST /diarizations/upload`

```bash
curl -s http://127.0.0.1:8092/diarizations/by-path \
  -H 'Content-Type: application/json' \
  -d '{"audio_path":"./input/test2.m4a"}'
```

### 5-3. 요약 API
- `POST /summaries`

설명:
- 입력은 `diarized transcript JSON payload`다.
- public contract에서는 `transcript_path` 대신 payload를 기본으로 사용한다.

```bash
curl -s http://127.0.0.1:8093/summaries \
  -H 'Content-Type: application/json' \
  -d '{"meeting_title":"03171354","transcript":{"provider":"overlap_policy_v1","segments":[]}}'
```

### 5-4. 오케스트레이션 API
- `POST /meeting-note-jobs/by-path`
- `POST /meeting-note-jobs/upload`
- `GET /meeting-note-jobs/{job_id}`

설명:
- 비동기 job 방식이다.
- orchestration API는 `meeting-transcriptions -> diarizations -> merge -> summaries -> txt export` 순서로 실행한다.
- job은 여러 개 접수할 수 있지만 내부 queue worker가 기본적으로 하나씩 처리한다.
- 상태/오류/산출물은 SQLite와 `logs/`, `output/`에 남긴다.

## 6. 운영 관점의 권장 구조
- `transcribe-api`
  - 웹의 음성 입력과 회의록 작성이 둘 다 호출할 수 있는 전사 서비스다.
  - 음성 입력은 `voice-transcriptions`, 회의록은 `meeting-transcriptions`를 쓴다.
  - 같은 resident ASR runtime을 공유하고, `voice`가 `meeting`보다 높은 우선순위를 가진다.
  - `meeting`에서만 align을 잠깐 로드하고 요청이 끝나면 unload한다.
- `diarize-api`
  - 회의록 작성 플로우에서만 사용한다.
  - 기본 동시성은 `1`이다.
- `summarize-api`
  - diarized transcript를 받아 요약만 수행한다.
  - 기본 동시성은 `1`이다.
- `asr-api`
  - 회의록 작성 버튼에서 호출하는 오케스트레이션 API다.
  - front-end는 job 생성과 상태 조회만 신경 쓰면 된다.
  - 실제 회의록 job은 queue worker가 기본 `1개`씩 처리한다.

## 7. 요구 환경
- Linux 서버
- `asr` 프로젝트: Python `3.10.12`, `uv 0.9.22`
- `vllm` 프로젝트: Python `3.12.12`, `vllm 0.15.0`
- `uv`
- ffmpeg 설치
- production 모드에서는 GPU용 `torch 2.8.0+cu126`, `torchaudio 2.8.0+cu126`, `qwen-asr`, `pyannote.audio 4.0.4`
- resident/model-serving API를 쓰려면 `api` group 설치가 필요하다
- `pyannote/speaker-diarization-community-1`를 사용한다
- GPU 배치는 현재 검증 예시에서 `GPU 0 = vLLM`, `GPU 1 = asr feature API/CLI` 이며, 실제 운영에서는 서버 자원/정책에 따라 바뀔 수 있다

## 8. 폴더 구조
- `input/`: 입력 오디오
- `work/`: 중간 산출물
- `output/`: 최종 산출물
- `logs/`: job 로그
- `src/cli/`: 기능별 CLI 진입점
- `src/api/`: orchestration API + feature API
- `src/runtime/`: resident 모델 로딩/추론 런타임
- `src/services/`: 서비스 계층과 orchestration helper
- `src/clients/`: 외부 서비스/feature API client
- `tests/`: 단위 테스트

## 9. 환경 변수
`.env.example`를 참고한다. 핵심 항목은 다음과 같다.

- `PIPELINE_MODE=production|mock`
- `WORK_ROOT`, `OUTPUT_ROOT`, `LOG_ROOT`, `INPUT_ROOT`
- `DB_URL`
- `ASR_COMMAND`, `ALIGN_COMMAND`, `DIARIZATION_COMMAND`
- `ASR_DEVICE`, `ALIGN_DEVICE`, `DIARIZATION_DEVICE`
- `SUMMARY_PROVIDER`, `SUMMARY_BASE_URL`, `SUMMARY_ENDPOINT_PATH`, `SUMMARY_MODEL`
- `TRANSCRIBE_API_BASE_URL`, `DIARIZE_API_BASE_URL`, `SUMMARIZE_API_BASE_URL`
- `MEETING_JOB_WORKERS`, `TRANSCRIBE_MAX_CONCURRENCY`
- `VOICE_MAX_PENDING`, `VOICE_WAIT_TIMEOUT_SEC`
- `MEETING_TRANSCRIBE_MAX_PENDING`, `DIARIZE_MAX_CONCURRENCY`, `SUMMARIZE_MAX_CONCURRENCY`

현재 검증된 요약 설정은 아래와 같다.

```env
SUMMARY_PROVIDER=vllm_generate
SUMMARY_BASE_URL=http://127.0.0.1:8120
SUMMARY_ENDPOINT_PATH=/v1/chat/completions
SUMMARY_MODEL=gpt-oss-120b
```

현재 검증된 서비스 연결 설정은 아래와 같다.

```env
TRANSCRIBE_API_BASE_URL=http://127.0.0.1:8091
DIARIZE_API_BASE_URL=http://127.0.0.1:8092
SUMMARIZE_API_BASE_URL=http://127.0.0.1:8093
```

## 10. 테스트
기본 테스트:

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
```

`pytest`를 설치한 경우:

```bash
uv run pytest -q
```

## 11. 운영 체크포인트
문제가 났을 때는 아래 순서로 본다.

1. `asr` 런타임 확인

```bash
cd /root/project/asr
uv run python -V
uv run python -c "import torch, torchaudio; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.device_count(), torchaudio.__version__)"
```

2. 기능 API 준비 상태 확인

```bash
curl -s http://127.0.0.1:8091/health
curl -s http://127.0.0.1:8092/health
curl -s http://127.0.0.1:8093/health
```

3. orchestration API 준비 상태 확인

```bash
curl -s http://127.0.0.1:${ORCH_PORT:-8090}/health
```

4. `vllm` 서버 확인

```bash
cd /root/project/vllm
ss -ltnp | grep 8120
ps -ef | grep 'vllm serve' | grep -v grep
tail -n 80 logs/$(ls -t logs | head -n 1)
```

5. GPU 배치 확인

```bash
nvidia-smi
```

## 12. 런타임 정리
```bash
bash scripts/clean_runtime.sh
```
