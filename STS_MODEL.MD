# STS (Speech-to-Speech) AI 모델 구축 설계서

> 작성일: 2026-06-24  
> 목표: Gemini Live Flash 수준의 음성 입력 → 음성 출력 AI 비서 자체 구축  
> 방식: **오디오 LLM (End-to-End)** — 별도 STT/TTS 없이 단일 모델로 처리  
> 기반: HuggingFace 오픈소스 모델 + Mac Mini M4 (24GB) 로컬 실행

---

## 왜 오디오 LLM인가

```
파이프라인 방식 (STT → LLM → TTS)
  마이크 → [Whisper 1초] → [LLM 2초] → [TTS 0.5초] → 스피커
  총 지연: 3~4초 → 콜센터처럼 답답한 느낌

오디오 LLM 방식 (End-to-End)
  마이크 → [Qwen2.5-Omni 단일 처리] → 스피커
  총 지연: 0.5~1.5초 → 자연스러운 대화 가능
```

---

## 전체 아키텍처

```
마이크 (실시간 음성)
      │
      ▼
┌──────────────────────────────────────────┐
│  VAD (Silero VAD)                        │
│  말이 끝나는 시점 자동 감지 (1.8MB 초경량) │
└──────────────┬───────────────────────────┘
               │ 음성 청크
               ▼
┌──────────────────────────────────────────┐
│  Qwen2.5-Omni-7B                         │
│  (End-to-End 오디오 LLM)                 │
│                                          │
│  - 음성 직접 이해 (STT 불필요)            │
│  - 추론 및 답변 생성                      │
│  - 음성으로 직접 출력 (TTS 불필요)         │
│  - 한국어 지원                            │
│  - Apple Silicon GPU 가속                │
└──────────────┬───────────────────────────┘
               │ 음성 스트림
               ▼
스피커 (음성 출력)
```

---

## 핵심 모델 분석

### Qwen2.5-Omni 계열 비교

| 모델 | 크기 | 특징 | M4 24GB 실행 | 추천 |
|------|------|------|-------------|------|
| **Qwen2.5-Omni-3B** | ~6GB | 가볍고 빠름, 기본 품질 | ✅ 여유 | ★★☆ 테스트용 |
| **Qwen2.5-Omni-7B** | ~15GB | 품질/속도 균형 최적 | ✅ 적합 | ✅ **1순위** |
| **Qwen2.5-Omni-7B-AWQ** | ~8GB | 양자화, 더 빠름 | ✅ 여유 | ✅ **속도 우선** |
| Qwen2.5-Omni-72B | ~45GB | 최고 품질 | ❌ 불가 | - |

> **추천**: `Qwen2.5-Omni-7B-AWQ` — 양자화로 메모리 절약 + 속도 향상

### Qwen2.5-Omni 지원 기능

```
입력 가능      출력 가능
──────────     ──────────
✅ 음성         ✅ 텍스트
✅ 텍스트       ✅ 음성 (Thinker-Talker 구조)
✅ 이미지
✅ 비디오
✅ 오디오 파일
```

### VAD (음성 감지)

| 모델 | 크기 | 역할 |
|------|------|------|
| **Silero VAD** | 1.8MB | 말이 끝나는 시점 감지 → 모델에 전달 타이밍 결정 |

---

## 구현 로드맵

```
Week 1: 환경 구성 및 모델 테스트
├── Python 3.11 + venv 환경 구성
├── Qwen2.5-Omni-7B HuggingFace에서 다운로드
├── 텍스트 입력 → 음성 출력 기본 테스트
└── 음성 입력 → 텍스트 응답 테스트

Week 2: 음성 ↔ 음성 연결
├── Silero VAD로 마이크 음성 감지 구현
├── 음성 입력 → Omni → 음성 출력 풀 파이프라인 연결
├── 한국어 대화 품질 테스트
└── Apple Silicon MPS 가속 최적화

Week 3: 백엔드 API 서버
├── FastAPI + WebSocket 서버 구성
├── 실시간 음성 스트리밍 처리
├── 대화 히스토리 관리 (멀티턴)
└── 응답 스트리밍 (생성 즉시 음성 출력)

Week 4: 웹 UI + 배포
├── React 마이크 인터페이스 구현
├── Docker 컨테이너화
├── Cloudflare Tunnel + Nginx 연결
└── 아이폰 외부 접속 테스트
```

---

## 기술 스택

```
┌─────────────────────────────────────────────────────┐
│  프론트엔드 (React + WebRTC)                         │
│  마이크 캡처 → WebSocket 전송 → 음성 재생            │
└─────────────────────┬───────────────────────────────┘
                      │ WebSocket (음성 바이트)
┌─────────────────────▼───────────────────────────────┐
│  백엔드 (FastAPI + Python)                           │
│  /ws/voice  ← 실시간 음성 스트림 처리                │
└──────┬──────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│  Silero VAD                                         │
│  발화 종료 시점 감지                                  │
└──────┬──────────────────────────────────────────────┘
       │ 음성 청크
┌──────▼──────────────────────────────────────────────┐
│  Qwen2.5-Omni-7B                                    │
│  (HuggingFace Transformers + MPS 가속)               │
│  음성 이해 → 추론 → 음성 생성                         │
└──────┬──────────────────────────────────────────────┘
       │ 음성 스트림
       ▼
   스피커 / 클라이언트 재생
```

---

## 핵심 코드 설계

### 모델 로딩

```python
from transformers import Qwen2_5OmniModel, Qwen2_5OmniProcessor
import torch

class OmniSTS:
    def __init__(self):
        model_id = "Qwen/Qwen2.5-Omni-7B"

        self.processor = Qwen2_5OmniProcessor.from_pretrained(model_id)
        self.model = Qwen2_5OmniModel.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            device_map="auto",          # Apple Silicon MPS 자동 감지
        )
        self.history = []

    def voice_chat(self, audio_input: bytes) -> bytes:
        # 음성 입력 → 모델 처리 → 음성 출력
        inputs = self.processor(
            audio=audio_input,
            return_tensors="pt"
        ).to(self.model.device)

        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=512,
                audio_output=True       # 음성으로 직접 출력
            )

        audio_response = self.processor.decode_audio(output)
        return audio_response
```

### FastAPI WebSocket 서버

```python
from fastapi import FastAPI, WebSocket
from omni import OmniSTS
from vad import SileroVAD

app = FastAPI()
omni = OmniSTS()
vad = SileroVAD()

@app.websocket("/ws/voice")
async def voice_stream(websocket: WebSocket):
    await websocket.accept()

    audio_buffer = b""

    while True:
        chunk = await websocket.receive_bytes()
        audio_buffer += chunk

        # VAD: 말이 끝났는지 감지
        if vad.is_speech_ended(audio_buffer):
            # Qwen2.5-Omni로 처리
            audio_response = omni.voice_chat(audio_buffer)

            # 음성 응답 전송
            await websocket.send_bytes(audio_response)
            audio_buffer = b""
```

---

## 폴더 구조

```
~/docker/ai/sts/
│
├── docker-compose.yml
├── .env
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py              ← FastAPI + WebSocket
│   ├── omni.py              ← Qwen2.5-Omni 서비스
│   └── vad.py               ← Silero VAD 서비스
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── App.tsx
│       └── components/
│           ├── VoiceButton.tsx    ← 마이크 버튼
│           └── AudioPlayer.tsx    ← 응답 재생
│
└── models/                  ← 모델 캐시 (볼륨 마운트)
    └── qwen2.5-omni-7b/
```

---

## docker-compose.yml

```yaml
services:
  sts-backend:
    build: ./backend
    container_name: sts-backend
    restart: always
    ports:
      - "8000:8000"
    volumes:
      - ./models:/root/.cache/huggingface   # 모델 캐시 유지
      - ./backend:/app
    environment:
      - MODEL_ID=Qwen/Qwen2.5-Omni-7B
      - DEVICE=mps                           # Apple Silicon GPU
    deploy:
      resources:
        reservations:
          memory: 18G

  sts-frontend:
    build: ./frontend
    container_name: sts-frontend
    restart: always
    ports:
      - "3050:3000"
    environment:
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/voice
```

---

## 성능 목표

```
Mac Mini M4 24GB 기준

Qwen2.5-Omni-7B 메모리 사용  : ~15GB
남은 메모리 (OS + 기타)       :  ~9GB

응답 지연 목표
  첫 음성 출력까지            : 0.5 ~ 1.5초
  자연스러운 대화 체감         : ✅ 가능
```

---

## Week 1 파일럿 테스트

> API/배포 없이 로컬에서 STS 동작 가능 여부만 검증  
> 파일 위치: `~/todo_list/pilot/`

### 파일럿 구성 파일

```
pilot/
├── setup.sh                 ← 환경 셋업 (1회 실행)
├── requirements.txt         ← Python 의존성
├── README.md                ← 파일럿 빠른 시작 안내
├── harness.py               ← 구조 계약 검증 (모델 불필요, 어디서나 실행)
├── 01_test_text.py          ← STEP 1: 텍스트 입출력 기본 확인
├── 02_test_audio_out.py     ← STEP 2: 텍스트 → 음성 파일 출력
├── 03_test_voice_chat.py    ← STEP 3: 음성 파일 → 음성 응답 (STS 핵심)
└── 04_test_realtime.py      ← STEP 4: 마이크 실시간 대화 (VAD 포함)
```

> 지속관리 규칙은 저장소 루트 `CLAUDE.md` 참고.
> 파일럿을 수정하면 `python pilot/harness.py` 로 설계 계약 일치를 검증할 것.

### 실행 순서

```bash
# 1. 파일럿 폴더로 이동
cd ~/todo_list/pilot

# 2. 환경 셋업 (최초 1회)
bash setup.sh

# 3. 가상환경 활성화
source ~/sts-pilot-venv/bin/activate

# 4. MPS(Apple Silicon GPU) 동작 확인
python -c "import torch; print('MPS 사용 가능:', torch.backends.mps.is_available())"

# 5. 단계별 테스트 실행
python 01_test_text.py                        # 텍스트 기본 동작
python 02_test_audio_out.py                   # 음성 출력 확인
python 03_test_voice_chat.py --record         # STS 핵심 검증
python 04_test_realtime.py                    # 실시간 대화 루프
```

### 단계별 검증 목표

| 단계 | 파일 | 검증 내용 | 성공 기준 |
|------|------|---------|---------|
| STEP 1 | `01_test_text.py` | 모델 로드 + 한국어 텍스트 응답 | 응답 출력됨 |
| STEP 2 | `02_test_audio_out.py` | 텍스트 → WAV 파일 생성 | `output_audio.wav` 재생 가능 |
| STEP 3 | `03_test_voice_chat.py` | 음성 입력 → 음성 응답 | 말하면 음성으로 답함 |
| STEP 4 | `04_test_realtime.py` | 상담사 인사 후 VAD 실시간 대화 | 연결 시 인사말 음성 → 연속 대화 |

> STEP 4는 연결 직후 상담사 페르소나로 **"안녕하세요, 무엇이 궁금하신가요?"** 를 먼저 음성 안내한 뒤 듣기를 시작한다.
> 페르소나/인사말은 `04_test_realtime.py` 상단의 `SYSTEM_PROMPT`, `GREETING_TEXT` 상수에서 수정. 서비스용 상세 프롬프트는 추후 별도 작성.

### 파일럿 모델 선택

```
처음 테스트 → Qwen2.5-Omni-3B (6GB, 빠른 다운로드)
  01_test_text.py 상단: MODEL_ID = "Qwen/Qwen2.5-Omni-3B"

품질 검증   → Qwen2.5-Omni-7B (15GB)
  01_test_text.py 상단: MODEL_ID = "Qwen/Qwen2.5-Omni-7B"
```

### 파일럿 통과 기준

```
✅ STEP 1 통과: 모델이 한국어로 정상 응답
✅ STEP 2 통과: output_audio.wav 생성 및 스피커 재생
✅ STEP 3 통과: 내 음성 → 음성 응답, 지연 3초 이내
✅ STEP 4 통과: 연속 대화 루프 정상 동작

→ 4단계 모두 통과 시 API 서버 + 배포 단계 진행
```

---

## 구축 체크리스트

### 파일럿 (Week 1)
- [ ] `bash setup.sh` 실행 — 환경 구성
- [ ] HuggingFace 계정 생성 및 `huggingface-cli login`
- [ ] Qwen2.5-Omni-3B 다운로드 (~6GB)
- [ ] `01_test_text.py` 통과
- [ ] `02_test_audio_out.py` 통과
- [ ] `03_test_voice_chat.py --record` 통과
- [ ] `04_test_realtime.py` 통과
- [ ] 지연 시간 기록 (목표: 3초 이내)

### 본 구현 (Week 2~4, 파일럿 통과 후)
- [ ] Qwen2.5-Omni-7B 교체 및 품질 비교
- [ ] FastAPI WebSocket 서버 구현
- [ ] React 마이크 → WebSocket → 스피커 구현
- [ ] Dockerfile 작성 및 docker-compose.yml 실행
- [ ] NPM에 `ai.내도메인.org` 프록시 등록
- [ ] 아이폰 외부 접속 음성 대화 테스트

---

## 참고 리소스

| 항목 | 링크 |
|------|------|
| Qwen2.5-Omni-7B | https://huggingface.co/Qwen/Qwen2.5-Omni-7B |
| Qwen2.5-Omni 논문/데모 | https://github.com/QwenLM/Qwen2.5-Omni |
| Silero VAD | https://github.com/snakers4/silero-vad |
| HuggingFace Transformers | https://huggingface.co/docs/transformers |

---

> 💡 **핵심**  
> Qwen2.5-Omni-7B 하나로 STT + 추론 + TTS를 모두 처리하기 때문에  
> 모델 간 데이터 변환 지연이 없고 문맥을 그대로 유지한 채 응답합니다.  
> Mac Mini M4 24GB에서 단독 실행 시 메모리 여유가 있습니다.
