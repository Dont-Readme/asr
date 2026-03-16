# asr-meeting-pipeline

## 1. 한 줄 요약
회의 음성 파일을 전사, 화자 분리, 요약하여 텍스트 회의록으로 내보내는 서버 실행용 CLI 파이프라인이다.

## 2. 현재 구현 범위
- `run_pipeline.py` 기반 단일 파일 배치 실행
- 단계별 산출물 저장: `work/<job_id>`, `output/<job_id>`, `logs/<job_id>.log`
- SQLite 기반 job 상태/산출물 기록
- 실제 동작 단계: preprocess, merge, summarize(vLLM client), export
- production adapter: Qwen3-ASR, Qwen3-ForcedAligner, pyannote diarization
- `mock` 모드도 유지되어 smoke test 가능

## 3. 빠른 시작
```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel
pip install -r requirements.txt
```

GPU 서버에서는 torch를 먼저 설치한 뒤 adapter 의존성을 추가한다.

```bash
# 예시: CUDA 12.4
pip install "torch==2.6.0" "torchaudio==2.6.0" --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.server.txt

cp .env.example .env
```

기본 smoke test는 mock 모드로 실행할 수 있다.

```bash
python run_pipeline.py ./input/test1.m4a \
  --meeting-title "주간 제품 회의" \
  --pipeline-mode mock
```

production 모드에서는 `.env.example`에 들어있는 기본 adapter 커맨드를 그대로 쓸 수 있다.
필수 조건:
- `ffmpeg` 설치
- GPU용 `torch`, `torchaudio` 설치
- `qwen-asr`, `pyannote.audio` 설치
- `HUGGINGFACE_HUB_TOKEN` 설정(pyannote 접근 시 필요)

```bash
env CUDA_VISIBLE_DEVICES=1 python run_pipeline.py ./input/test1.m4a --meeting-title "주간 제품 회의"
nohup env CUDA_VISIBLE_DEVICES=1 python run_pipeline.py ./input/test1.m4a --meeting-title "주간 제품 회의" > ./logs/nohup_test1.log 2>&1 &
```

## 4. 요구 환경
- Linux 서버
- Python 3.10+
- ffmpeg 설치
- production 모드에서는 GPU용 torch/torchaudio, qwen-asr, pyannote.audio
- `pyannote/speaker-diarization-community-1`를 쓸 경우 `pyannote.audio 4.x` 필요
- CUDA 12.4 + 공식 wheel 제약이 있으면 `pyannote/speaker-diarization-3.1` + `pyannote.audio 3.3.2`가 더 안정적일 수 있음

## 5. 폴더 구조
- `input/`: 입력 오디오
- `work/`: 중간 산출물
- `output/`: 최종 산출물
- `logs/`: job 로그
- `src/`: 파이프라인 코드
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

## 7. 테스트
현재 테스트는 `unittest` 호환으로 작성되어 추가 패키지 없이 실행할 수 있다.

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

`pytest`를 설치한 경우 다음도 가능하다.

```bash
pytest -q
```

## 8. 문제 해결
- ffmpeg 실패: `ffmpeg -version` 확인
- SQLite 생성 실패: `DB_URL` 경로와 쓰기 권한 확인
- vLLM 호출 실패: `SUMMARY_BASE_URL`와 `SUMMARY_ENDPOINT_PATH` 확인
- Qwen 모델 로드 실패: `torch` CUDA wheel, `ASR_DEVICE`, `ALIGN_DEVICE` 확인
- pyannote 로드 실패: `HUGGINGFACE_HUB_TOKEN`과 모델 약관 동의 확인
- `SpeakerDiarization.__init__(... plda ...)` 오류: `pyannote.audio`를 4.x로 업그레이드
- `huggingface-hub==1.x` 충돌: `uv pip install "huggingface-hub>=0.34,<1.0" "transformers==4.57.6"`
- `torchaudio.list_audio_backends` 오류: `torch`와 `torchaudio`를 같은 버전의 2.9 미만으로 다시 맞춰 설치. `cu124` 예시는 `2.6.0`
- `NameError: AudioDecoder`: `pyannote.audio 4.x`가 기대하는 `torchcodec` 디코더 스택이 깨진 상태. 가장 쉬운 우회는 `pyannote/speaker-diarization-3.1` + `pyannote.audio 3.3.2`
- production stage 실패: `ASR_COMMAND`, `ALIGN_COMMAND`, `DIARIZATION_COMMAND` 설정 확인

## 9. 다음 확장 포인트
- 긴 회의 transcript chunking 후 summarize
- Postgres + migration 도입
