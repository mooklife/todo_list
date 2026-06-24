# STS 파일럿 (Week 1)

Qwen2.5-Omni 기반 음성→음성(STS) 동작 가능성을 로컬에서 검증하는 파일럿입니다.
전체 설계는 상위 폴더의 [`STS_MODEL.MD`](../STS_MODEL.MD), 관리 규칙은 [`CLAUDE.md`](../CLAUDE.md) 참고.

## 구성

| 파일 | 단계 | 내용 |
|------|------|------|
| `setup.sh` | - | Mac 환경 셋업 (1회) |
| `requirements.txt` | - | Python 의존성 |
| `01_test_text.py` | STEP 1 | 텍스트 입출력 기본 동작 |
| `02_test_audio_out.py` | STEP 2 | 텍스트 → 음성 파일 출력 |
| `03_test_voice_chat.py` | STEP 3 | 음성 → 음성 응답 (STS 핵심) |
| `04_test_realtime.py` | STEP 4 | 마이크 실시간 대화 (VAD) |
| `harness.py` | 검증 | 구조 계약 검증 (모델 불필요) |

## 빠른 시작 (Mac, Apple Silicon)

```bash
bash setup.sh
source ~/sts-pilot-venv/bin/activate
python 01_test_text.py
python 02_test_audio_out.py
python 03_test_voice_chat.py --record
python 04_test_realtime.py
```

## 어디서나 가능한 구조 검증 (모델·토치 불필요)

```bash
python harness.py
```

- Windows 포함 어느 환경에서나 실행 가능 (stdlib만 사용).
- 파일럿을 수정한 뒤에는 반드시 이 하네스를 통과시키세요(종료코드 0).

## 주의

- 가상환경/모델 가중치/생성된 `*.wav` 는 git에 커밋하지 않습니다(`.gitignore` 처리).
- 모델 실행은 Apple Silicon(MPS)에서만 실용적입니다. Windows는 하네스 검증 용도로만.
