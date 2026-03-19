# API SPEC

## 1. 개요
현재 API는 4개 프로세스로 나뉜다.

- orchestration API
  - 기본 포트: `8080`
  - 실제 서버에서 `8080`이 이미 점유된 경우 `8090` 같은 빈 포트를 사용한다
  - 역할: 회의록 작성 job 생성, 상태 조회
- transcribe API
  - 기본 포트: `8091`
  - 역할: 음성 입력용 전사, 회의록용 전사+align
- diarize API
  - 기본 포트: `8092`
  - 역할: 화자 분리
- summarize API
  - 기본 포트: `8093`
  - 역할: diarized transcript payload 요약

## 2. Orchestration API
Base URL 예시: `http://127.0.0.1:8090`

### `GET /health`
응답:

```json
{
  "status": "ready"
}
```

### `POST /meeting-note-jobs/by-path`
설명:
- 서버에 이미 있는 음성 파일 경로를 받아 회의록 job을 생성한다.
- 즉시 `job_id`를 반환하고, 실제 처리는 내부 queue worker가 순차로 수행한다.

요청:

```json
{
  "audio_path": "./input/test2.m4a",
  "meeting_title": "03171354",
  "language": "ko",
  "output_root": null,
  "work_root": null,
  "log_root": null,
  "pipeline_mode": null,
  "overwrite": false
}
```

응답:

```json
{
  "job_id": "03171354-c7bb5a06",
  "meeting_title": "03171354",
  "status": "PENDING",
  "status_url": "/meeting-note-jobs/03171354-c7bb5a06"
}
```

### `POST /meeting-note-jobs/upload`
설명:
- multipart 업로드로 음성 파일을 받아 회의록 job을 생성한다.

Form fields:
- `file`: 업로드 파일
- `meeting_title`: optional
- `language`: optional, default `ko`
- `output_root`: optional
- `work_root`: optional
- `log_root`: optional
- `pipeline_mode`: optional
- `overwrite`: optional, default `false`

응답:
- `/meeting-note-jobs/by-path` 와 동일

### `GET /meeting-note-jobs/{job_id}`
설명:
- job 상태와 산출물 목록을 반환한다.

응답:

```json
{
  "job": {
    "id": "03171354-c7bb5a06",
    "status": "DONE",
    "current_stage": "EXPORT",
    "input_path": "/root/project/asr/input/test2.m4a",
    "meeting_title": "03171354",
    "language": "ko",
    "work_dir": "/root/project/asr/work/03171354-c7bb5a06",
    "output_dir": "/root/project/asr/output/03171354-c7bb5a06",
    "log_path": "/root/project/asr/logs/03171354-c7bb5a06.log",
    "error_stage": null,
    "error_message": null,
    "created_at": "2026-03-17T05:00:00Z",
    "updated_at": "2026-03-17T05:46:00Z"
  },
  "artifacts": [
    {
      "file_type": "transcript_diarized_json",
      "path": "/root/project/asr/output/03171354-c7bb5a06/transcript_diarized.json",
      "sha256": "..."
    }
  ]
}
```

별칭:
- `GET /jobs/{job_id}` 도 동일하게 지원한다.

## 3. Transcribe API
Base URL 예시: `http://127.0.0.1:8091`

### `GET /health`
응답:

```json
{
  "status": "ready",
  "loaded_at": "2026-03-18T00:00:00Z",
  "process_id": 12345,
  "device": "cuda",
  "models": {
    "asr": "Qwen/Qwen3-ASR-1.7B",
    "align": "Qwen/Qwen3-ForcedAligner-0.6B"
  }
}
```

### `POST /voice-transcriptions/by-path`
설명:
- 음성 입력용 전사
- `ASR-only`
- 같은 resident transcribe runtime을 쓰는 `meeting-transcriptions`보다 높은 우선순위를 가진다.
- transcribe API는 공용 실행 슬롯 1개를 공유하므로, 이미 다른 전사 작업이 실행 중이면 잠시 대기하거나 `503`으로 거절될 수 있다.

요청:

```json
{
  "audio_path": "./input/test2.m4a",
  "language": "ko",
  "context": null
}
```

응답:

```json
{
  "text": "사용자 명령어 전체 텍스트",
  "asr": {
    "provider": "qwen_asr",
    "model": "Qwen/Qwen3-ASR-1.7B",
    "language": "Korean",
    "segments": []
  },
  "elapsed_sec": 1.234
}
```

### `POST /voice-transcriptions/upload`
설명:
- multipart 업로드 버전

Form fields:
- `file`: 업로드 파일
- `language`: optional
- `context`: optional

응답:
- `/voice-transcriptions/by-path` 와 동일

### `POST /meeting-transcriptions/by-path`
설명:
- 회의록용 전사
- `ASR + align`
- `voice-transcriptions`와 같은 resident transcribe runtime을 공유한다.
- align runtime은 요청 처리 중에만 로드되고, 응답 후 unload된다.

요청:

```json
{
  "audio_path": "./input/test2.m4a",
  "language": "ko",
  "context": null
}
```

응답:

```json
{
  "text": "정렬 기준 전체 텍스트",
  "asr": {
    "provider": "qwen_asr",
    "model": "Qwen/Qwen3-ASR-1.7B",
    "language": "Korean",
    "segments": []
  },
  "align": {
    "provider": "qwen_forced_aligner",
    "model": "Qwen/Qwen3-ForcedAligner-0.6B",
    "segments": []
  },
  "elapsed_sec": 2.345
}
```

### `POST /meeting-transcriptions/upload`
설명:
- multipart 업로드 버전

Form fields:
- `file`: 업로드 파일
- `language`: optional
- `context`: optional

응답:
- `/meeting-transcriptions/by-path` 와 동일

## 4. Diarize API
Base URL 예시: `http://127.0.0.1:8092`

설명:
- resident diarization runtime을 재사용한다.
- 기본 실행 동시성은 `1`이다.

### `GET /health`
응답:

```json
{
  "status": "ready",
  "loaded_at": "2026-03-18T00:00:00Z",
  "process_id": 12345,
  "device": "cuda",
  "models": {
    "diarization": "pyannote/speaker-diarization-community-1"
  }
}
```

### `POST /diarizations/by-path`
요청:

```json
{
  "audio_path": "./input/test2.m4a",
  "num_speakers": null,
  "min_speakers": null,
  "max_speakers": null
}
```

응답:

```json
{
  "diarization": {
    "provider": "pyannote.audio",
    "model": "pyannote/speaker-diarization-community-1",
    "speakers": []
  },
  "rttm": "SPEAKER ...",
  "elapsed_sec": 3.456
}
```

### `POST /diarizations/upload`
설명:
- multipart 업로드 버전

Form fields:
- `file`: 업로드 파일
- `num_speakers`: optional
- `min_speakers`: optional
- `max_speakers`: optional

응답:
- `/diarizations/by-path` 와 동일

## 5. Summarize API
Base URL 예시: `http://127.0.0.1:8093`

설명:
- 외부 `vLLM` 서버를 호출한다.
- API 레벨 기본 실행 동시성은 `1`이다.

### `GET /health`
응답:

```json
{
  "status": "ready",
  "loaded_at": "2026-03-18T00:00:00Z",
  "process_id": 12345,
  "device": "external",
  "models": {
    "summary": "gpt-oss-120b"
  }
}
```

### `POST /summaries`
설명:
- `diarized transcript JSON payload`를 받아 summary JSON을 반환한다.

요청:

```json
{
  "meeting_title": "03171354",
  "transcript": {
    "provider": "overlap_policy_v1",
    "segments": [
      {
        "speaker_label": "화자 A",
        "start_sec": 0.0,
        "end_sec": 1.0,
        "text": "안녕하세요",
        "line": "[00:00:00] 화자 A: 안녕하세요",
        "words": []
      }
    ]
  }
}
```

응답:

```json
{
  "summary": {
    "meeting_title": "03171354",
    "provider": "vllm_generate",
    "summary": [],
    "decisions": [],
    "action_items": []
  },
  "elapsed_sec": 4.567
}
```

## 6. 에러 규칙
- 성공: `200`
- 잘못된 요청/실행 오류: `400`
- busy / queue wait timeout: `503`
- 존재하지 않는 job 조회: `404`

에러 응답 예시:

```json
{
  "detail": "[SUMMARIZE] vLLM 연결 실패: [Errno 111] Connection refused"
}
```
