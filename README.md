# asr-meeting-pipeline

## 1. 한 줄 요약
회의 음성 파일을 전사, 화자 분리, 요약하여 텍스트 회의록으로 내보내는 서버 실행용 파이프라인이며, 기능별 CLI와 FastAPI 진입점을 함께 제공한다.

## 2. 현재 구현 범위
- `uv` 기반 단일 프로젝트 패키징(`pyproject.toml`)
- 기능별 실행 진입점: `asr-transcribe`, `asr-diarize`, `asr-summarize`, `asr-pipeline`
- resident API 진입점: `asr-transcribe-api`, `asr-diarize-api`
- `run_pipeline.py` 호환 래퍼 유지
- FastAPI skeleton: `/transcriptions`, `/diarizations`, `/summaries`, `/pipelines`, `/jobs/{job_id}`
- resident FastAPI: `/health`, `/transcribe`, `/diarize`
- 현재 검증된 운영 경로는 CLI 배치 실행이다
- 단계별 산출물 저장: `work/<job_id>`, `output/<job_id>`, `logs/<job_id>.log`
- SQLite 기반 job 상태/산출물 기록
- 실제 동작 단계: preprocess, merge, summarize(vLLM client), export
- production adapter: Qwen3-ASR, Qwen3-ForcedAligner, pyannote diarization
- `mock` 모드도 유지되어 smoke test 가능

## 3. 빠른 시작
현재 검증된 서버 기준 실행 절차는 다음과 같다.

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

5. 전체 파이프라인 실행

```bash
cd /root/project/asr
env CUDA_VISIBLE_DEVICES=1 uv run asr-pipeline ./input/test2.m4a --meeting-title "03171354"
```

6. 요약만 다시 실행

```bash
cd /root/project/asr
uv run asr-summarize ./output/<job_id>/transcript_diarized.json --meeting-title "03171354"
```

7. 런타임 산출물 정리

```bash
bash scripts/clean_runtime.sh
```

기능별 실행도 가능하다.

```bash
uv run asr-transcribe ./input/test1.m4a --meeting-title "주간 제품 회의" --pipeline-mode mock
uv run asr-diarize ./input/test1.m4a --meeting-title "주간 제품 회의" --pipeline-mode mock
uv run asr-summarize ./output/job/transcript_diarized.json --meeting-title "주간 제품 회의" --pipeline-mode mock
uv run asr-api --host 0.0.0.0 --port 8080
uv run asr-transcribe-api --host 0.0.0.0 --port 8091
uv run asr-diarize-api --host 0.0.0.0 --port 8092
```

기본 smoke test는 mock 모드로 실행할 수 있다.

```bash
uv run asr-pipeline ./input/test1.m4a \
  --meeting-title "주간 제품 회의" \
  --pipeline-mode mock
```

실제 운영에서는 아래 순서를 권장한다.
- 먼저 `/root/project/vllm` 에서 120B 요약 서버를 띄운다
- `ss -ltnp | grep 8120` 로 요약 서버 준비 완료를 확인한다
- 그다음 `/root/project/asr` 에서 `env CUDA_VISIBLE_DEVICES=1 uv run asr-pipeline ...` 을 실행한다
- 요약만 다시 만들 때는 `uv run asr-summarize ...` 만 재실행한다

VRAM을 안정적으로 보려면 resident API를 사용한다.
- `asr-api` 는 thin wrapper라서 모델을 메모리에 계속 상주시켜 두지 않는다
- 실제 운영 관점에서는 `asr-api` 를 orchestration/control plane 으로 보고, resident API를 model-serving plane 으로 보는 편이 맞다
- `asr-transcribe-api` 는 startup 시 `Qwen3-ASR + ForcedAligner` 를 한 번만 올린다
- `asr-diarize-api` 는 startup 시 `pyannote` pipeline 을 한 번만 올린다
- VRAM 측정 시에는 `--reload` 를 쓰지 않는다

resident API 실행 예시:

```bash
cd /root/project/asr
bash scripts/run_transcribe_api.sh
```

```bash
cd /root/project/asr
bash scripts/run_diarize_api.sh
```

포트나 GPU를 바꾸려면 환경 변수로 덮어쓴다.

```bash
cd /root/project/asr
CUDA_DEVICE=0 PORT=8095 bash scripts/run_transcribe_api.sh
CUDA_DEVICE=1 PORT=8096 bash scripts/run_diarize_api.sh
```

resident API 준비 완료 확인:

```bash
curl -s http://127.0.0.1:8091/health
curl -s http://127.0.0.1:8092/health
```

resident API 호출 예시:

```bash
curl -s http://127.0.0.1:8091/transcribe \
  -H 'Content-Type: application/json' \
  -d '{"audio_path":"./input/test2.m4a","language":"ko"}'
```

```bash
curl -s http://127.0.0.1:8092/diarize \
  -H 'Content-Type: application/json' \
  -d '{"audio_path":"./input/test2.m4a"}'
```

## 4. 요구 환경
- Linux 서버
- `asr` 프로젝트: Python `3.10.12`, `uv 0.9.22`
- `vllm` 프로젝트: Python `3.12.12`, `vllm 0.15.0`
- `uv`
- ffmpeg 설치
- production 모드에서는 GPU용 `torch 2.8.0+cu126`, `torchaudio 2.8.0+cu126`, `qwen-asr`, `pyannote.audio 4.0.4`
- resident API를 쓰려면 `api` group 설치가 필요하다
- `pyannote/speaker-diarization-community-1`를 사용한다
- GPU 배치는 현재 검증 예시에서 `GPU 0 = vLLM`, `GPU 1 = asr pipeline` 이며, 실제 운영에서는 서버 자원/정책에 따라 바뀔 수 있다

## 5. 폴더 구조
- `input/`: 입력 오디오
- `work/`: 중간 산출물
- `output/`: 최종 산출물
- `logs/`: job 로그
- `src/cli/`: 기능별 CLI 진입점
- `src/services/`: 기능 서비스 계층
- `src/api/`: FastAPI 앱
- `src/runtime/`: resident 모델 로딩/추론 런타임
- `src/`: 파이프라인/adapter/client/schema 코드
- `tests/`: 단위 테스트

## 6. 환경 변수
`.env.example`를 참고한다. 핵심 항목은 다음과 같다.

- `PIPELINE_MODE=production|mock`
- `WORK_ROOT`, `OUTPUT_ROOT`, `LOG_ROOT`, `INPUT_ROOT`
- `DB_URL`
- `ASR_COMMAND`, `ALIGN_COMMAND`, `DIARIZATION_COMMAND`
- `ASR_DEVICE`, `ASR_DTYPE`, `ASR_CHUNK_MAX_SECONDS`
- `ALIGN_DEVICE`, `ALIGN_DTYPE`, `ALIGN_MAX_BATCH_SIZE`
- `DIARIZATION_DEVICE`, `DIARIZATION_NUM_SPEAKERS`
- `SUMMARY_PROVIDER=vllm_generate|mock`
- `SUMMARY_BASE_URL`, `SUMMARY_ENDPOINT_PATH`
- OpenAI 호환 vLLM이면 `SUMMARY_PROVIDER=vllm_openai_chat`, `SUMMARY_MODEL`, `SUMMARY_API_KEY`

현재 검증된 요약 설정은 아래와 같다.

```env
SUMMARY_PROVIDER=vllm_generate
SUMMARY_BASE_URL=http://127.0.0.1:8120
SUMMARY_ENDPOINT_PATH=/v1/chat/completions
SUMMARY_MODEL=gpt-oss-120b
```

설명:
- 현재 코드는 `SUMMARY_PROVIDER=vllm_generate` 이더라도 `SUMMARY_ENDPOINT_PATH=/v1/chat/completions` 이면 OpenAI chat payload로 자동 전환한다
- 따라서 지금 검증된 서버에서는 위 값을 그대로 쓰는 것이 가장 안전하다

현재 검증된 외부 커맨드 설정은 아래와 같다.

```env
ASR_COMMAND=.venv/bin/python -m src.adapters.qwen_asr --audio "{audio_path}" --output "{output_path}"
ALIGN_COMMAND=.venv/bin/python -m src.adapters.qwen_align --audio "{audio_path}" --input-json "{input_json}" --output "{output_path}"
DIARIZATION_COMMAND=.venv/bin/python -m src.adapters.pyannote_diarize --audio "{audio_path}" --output "{output_path}" --output-dir "{output_dir}"
```

## 7. 테스트
현재 테스트는 `unittest` 호환으로 작성되어 추가 패키지 없이 실행할 수 있다.

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
```

`pytest`를 설치한 경우 다음도 가능하다.

```bash
uv run pytest -q
```

## 8. 운영 체크포인트
문제가 났을 때는 아래 순서로 확인하면 된다.

1. `asr` 런타임이 정상인지 확인

```bash
cd /root/project/asr
uv run python -V
uv run python -c "import torch, torchaudio; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.device_count(), torchaudio.__version__)"
```

2. 핵심 `.env` 값이 맞는지 확인

```bash
cd /root/project/asr
grep -E '^(ASR_COMMAND|ALIGN_COMMAND|DIARIZATION_COMMAND|ASR_DEVICE|ALIGN_DEVICE|DIARIZATION_DEVICE|SUMMARY_PROVIDER|SUMMARY_BASE_URL|SUMMARY_ENDPOINT_PATH|SUMMARY_MODEL)=' .env
```

3. `vllm` 서버가 실제로 살아 있는지 확인

```bash
cd /root/project/vllm
ss -ltnp | grep 8120
ps -ef | grep 'vllm serve' | grep -v grep
tail -n 80 logs/$(ls -t logs | head -n 1)
```

4. GPU 배치가 맞는지 확인

```bash
nvidia-smi
```

현재 검증 예시:
- GPU 0: `gpt-oss-120b` vLLM 서버
- GPU 1: `asr-pipeline` 의 `ASR/ALIGN/DIARIZE`

주의:
- 위 GPU 배치는 현재 서버에서 검증한 예시일 뿐 고정 규칙이 아니다
- 실제 운영에서는 가용 VRAM, 다른 워크로드, 서버 정책에 따라 GPU 번호를 조정할 수 있다

5. 최신 산출물이 생성됐는지 확인

```bash
cd /root/project/asr
latest_job="$(ls -td output/* 2>/dev/null | head -n 1)"
echo "$latest_job"
find "$latest_job" -maxdepth 1 -type f | sort
```

6. resident API가 준비 완료인지 확인

```bash
curl -s http://127.0.0.1:8091/health
curl -s http://127.0.0.1:8092/health
```

7. VRAM 측정은 idle 과 peak 를 나눠서 본다

```bash
watch -n 1 nvidia-smi
```

추천 순서:
- `vLLM` 만 올렸을 때 GPU 0 idle VRAM 확인
- `asr-transcribe-api` 를 올렸을 때 GPU 1 idle VRAM 확인
- `asr-diarize-api` 를 올렸을 때 GPU 1 idle VRAM 확인
- representative 요청 1회로 first-request peak VRAM 확인
- 같은 요청을 3회 반복해 steady peak VRAM 확인

## 9. 문제 해결
- ffmpeg 실패: `ffmpeg -version` 확인
- SQLite 생성 실패: `DB_URL` 경로와 쓰기 권한 확인
- `uv sync`가 깨진 `.venv` 경고를 내면: `rm -rf .venv` 후 `uv sync --python 3.10 ...` 로 다시 만든다
- `Qwen ASR dependencies are missing: No module named 'qwen_asr'`: `uv sync --group transcribe ...`가 빠진 상태다
- `torch.cuda.is_available() is False`: `nvidia-smi`와 `uv run python -c "import torch; ..."`를 확인하고 GPU torch를 다시 설치한다
- `vLLM 연결 실패: [Errno 111] Connection refused`: `vllm` 서버가 아직 준비 안 되었거나 죽은 상태다. `ss -ltnp | grep 8120` 와 `tail -f /root/project/vllm/logs/...` 로 확인한다
- `vLLM HTTP 400`에 `Field required: messages`가 나오면 OpenAI 호환 endpoint에 `/generate` payload를 보낸 상태다. 현재 client는 `/v1/chat/completions`에서 chat payload로 자동 전환한다
- `vllm: not found` 또는 `bad interpreter`: `/root/project/vllm` 쪽 가상환경/PATH 문제다. `source .venv/bin/activate`, `which vllm`, `.venv/bin/vllm --help` 로 점검한다
- `ASR/ALIGN/DIARIZE` 인자 누락(`--audio`, `--input-json`) 오류: `.env`의 `ASR_COMMAND`, `ALIGN_COMMAND`, `DIARIZATION_COMMAND` 줄에 공백이 깨진 상태다
- Qwen 모델 로드 실패: `torch` CUDA wheel, `ASR_DEVICE`, `ALIGN_DEVICE` 확인
- pyannote 로드 실패: `HUGGINGFACE_HUB_TOKEN`과 모델 약관 동의 확인
- `SpeakerDiarization.__init__(... plda ...)` 오류: `pyannote.audio` 버전이 맞지 않는 상태다. 현재 검증값은 `4.0.4`
- `huggingface-hub==1.x` 충돌: `huggingface-hub>=0.34,<1.0` 범위를 맞춘다
- `torchcodec` 경고: 현재 diarization adapter는 waveform을 먼저 메모리로 읽어서 넘기므로 경고만으로 실패로 보지 않는다
- `NameError: AudioDecoder`: `pyannote.audio 4.x`가 기대하는 `torchcodec` 디코더 스택이 깨진 상태다. 현재 adapter는 이 경로를 우회하도록 작성돼 있다
- production stage 실패: `ASR_COMMAND`, `ALIGN_COMMAND`, `DIARIZATION_COMMAND` 설정 확인
- `env: 'python': No such file or directory`: `uv run ...`으로 실행하거나 `python3`/절대 경로 interpreter를 사용한다.
- resident API가 바로 종료되면: `uv sync --group api ...` 설치 여부와 `/health` 응답 여부를 먼저 확인한다
- resident API 수정 후 결과가 안 바뀌면: 상주 프로세스를 재시작해야 한다

VRAM 기준으로 모델 축소/양자화를 판단할 때는 아래 순서를 권장한다.
- idle VRAM + steady peak VRAM + 10~15% 여유가 한 GPU에 안 들어가면 먼저 운영 리스크가 있는 상태로 본다
- 전사 API가 여유 없이 1개 GPU를 거의 채우면 작은 ASR 모델 또는 양자화 후보를 검토한다
- 화자분리 API가 여유 없이 차면 pyannote 대체 모델이나 legacy fallback 조합을 검토한다
- 요약 서버가 GPU 대부분을 고정 점유하면 `120b -> 20b` 또는 양자화/동시성 축소를 우선 검토한다
- 양자화/모델 교체는 항상 동일 샘플 3개로 품질 비교 후 결정한다

## 10. 다음 확장 포인트
- 긴 회의 transcript chunking 후 summarize
- Postgres + migration 도입
- resident API 기준 VRAM/latency 계측 자동화
- resident API 결과를 pipeline orchestrator와 직결할지 결정
