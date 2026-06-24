# CLAUDE.md — STS 프로젝트 지속관리 지침

> 이 파일은 AI 에이전트(Claude/Cursor 등)와 사람이 **이 저장소를 어디서 clone 하든**
> 동일한 규칙으로 STS 설계와 파일럿을 유지·발전시키기 위한 단일 기준 문서입니다.
> 작업을 시작하기 전에 항상 이 파일을 먼저 읽으세요.

---

## 1. 프로젝트 개요

- **목표**: Gemini Live Flash 수준의 음성 입력 → 음성 출력(STS) AI 비서를 자체 구축
- **방식**: 오디오 LLM(End-to-End) — `Qwen2.5-Omni` 단일 모델로 STT/추론/TTS 통합
- **실행 환경**: Mac (Apple Silicon, MPS 가속). 최종 운영은 Mac Mini M4 24GB
- **현재 단계**: Week 1 파일럿 (로컬에서 STS 동작 가능성만 검증, API/배포 없음)

### 핵심 문서·디렉토리

| 경로 | 역할 |
|------|------|
| `STS_MODEL.MD` | **설계 단일 원천(SSOT)**. 아키텍처/로드맵/체크리스트 |
| `pilot/` | Week 1 파일럿 검증 스크립트 (01→04 순서) |
| `pilot/harness.py` | 파일럿이 설계와 어긋나지 않는지 검증하는 하네스 |
| `CLAUDE.md` | (이 파일) 지속관리 규칙 |

---

## 2. 황금 규칙 (항상 지킬 것)

1. **설계와 코드는 항상 동기화한다.**
   - `pilot/` 의 파일/함수/모델ID를 바꾸면 → `STS_MODEL.MD` 의 해당 섹션도 같은 커밋에서 갱신.
   - 반대로 `STS_MODEL.MD` 설계를 바꾸면 → 영향 받는 파일럿과 `harness.py` 계약도 갱신.

2. **파일럿을 바꾼 뒤에는 반드시 하네스를 통과시킨다.**
   ```bash
   python pilot/harness.py
   ```
   - 종료코드 0(PASS)이 아니면 작업을 끝내지 않는다.
   - 하네스는 외부 패키지 없이(stdlib만) 동작하므로 Windows/Mac 어디서나 실행 가능.

3. **파일럿 "계약(contract)"을 함부로 깨지 않는다.**
   - 계약 = 파일 목록, 각 파일의 필수 함수, 공통 `MODEL_ID`, 실행 순서.
   - 계약을 의도적으로 바꿀 때는 `harness.py` 의 `CONTRACT` 와 `STS_MODEL.MD` 를 함께 수정.

4. **검증 안 된 사실을 단정하지 않는다.**
   - 실제 모델 API 동작은 기기에서 확인 후 문서에 반영(아래 5절 참고).

5. **한국어로 응답/주석을 유지한다.** (사용자 선호)

---

## 3. 파일럿 계약 (Single Source of Truth)

`harness.py` 가 아래를 강제한다. 변경 시 두 곳을 함께 수정한다.

- 공통 모델: `MODEL_ID = "Qwen/Qwen2.5-Omni-3B"` (파일럿 기본) → 검증 후 `-7B` 로 승격
- 파일 및 필수 함수:

| 파일 | 필수 함수 |
|------|-----------|
| `01_test_text.py` | `load_model`, `text_chat`, `main` |
| `02_test_audio_out.py` | `load_model`, `text_to_speech`, `play_audio`, `main` |
| `03_test_voice_chat.py` | `load_model`, `record_audio`, `voice_to_voice`, `main` |
| `04_test_realtime.py` | `load_model`, `load_vad`, `detect_speech`, `voice_to_voice`, `realtime_loop`, `main` |

- 실행 순서: `01 → 02 → 03 → 04`
- 통과 기준: 4단계 모두 정상 + STEP 3 지연 3초 이내

---

## 4. 표준 작업 흐름

```
1) CLAUDE.md 읽기 (이 파일)
2) STS_MODEL.MD 에서 해당 섹션 확인
3) 코드/설계 수정
4) python pilot/harness.py  → PASS 확인
5) STS_MODEL.MD 동기화 (변경 내용 반영)
6) 커밋 (아래 메시지 컨벤션)
```

### 커밋 메시지 컨벤션
- `design:` 설계 문서(`STS_MODEL.MD`) 변경
- `pilot:` 파일럿 스크립트 변경
- `harness:` 하네스/계약 변경
- `docs:` 기타 문서
- 예) `pilot: STEP3 음성 응답 디코딩 방식 수정 + 설계 동기화`

---

## 5. 기기에서 검증할 항목 (Mac M2/M4)

> Windows에서는 모델 실행 불가(MPS/CUDA 없음). 아래는 Apple Silicon에서 확인.

- [ ] `torch.backends.mps.is_available()` → `True`
- [ ] **`model.generate()` 반환 형식 통일** ⚠️ (현재 파일럿의 최대 리스크)
  - `01`은 텐서(`output_ids[0]`), `02`/`03`은 객체(`output.audio`/`.sequences`)로 가정.
  - 실제 Qwen2.5-Omni는 `return_audio=True` 시 `(text_ids, audio)` 튜플 반환 가능.
  - 기기에서 실제 형식 확인 후 **네 파일 모두 동일한 처리 방식으로 통일**하고 문서 반영.
- [ ] 모델 클래스명 확인 (`Qwen2_5OmniModel` vs `Qwen2_5OmniForConditionalGeneration`)
- [ ] 음성 출력에 화자(speaker) 인자나 `qwen-omni-utils` 필요 여부 확인
- [ ] 한국어 음성 품질/지연 측정값을 `STS_MODEL.MD` "성능 목표"에 실측치로 갱신

---

## 6. 다른 환경에서 clone 했을 때

```bash
git clone <repo>
cd <repo>

# 1) 규칙 확인
#    CLAUDE.md → STS_MODEL.MD 순서로 읽기

# 2) 어디서나 가능한 구조 검증 (모델 불필요)
python pilot/harness.py

# 3) Mac(Apple Silicon)에서만: 실제 파일럿 실행
cd pilot
bash setup.sh
source ~/sts-pilot-venv/bin/activate
python 01_test_text.py
```

- `setup.sh`, 모델 캐시, 가상환경, 생성된 `*.wav` 는 `.gitignore` 로 저장소에서 제외됨.
- 따라서 clone 후에는 `setup.sh` 로 환경을 재구성하면 동일 상태가 된다.

---

## 7. 하지 말 것

- 가상환경(`*-venv/`), 모델 가중치, 생성된 오디오(`*.wav`)를 커밋하지 말 것.
- 하네스를 통과하지 못한 상태로 "완료" 처리하지 말 것.
- 설계와 코드 중 한쪽만 바꾸고 다른 쪽을 방치하지 말 것.
