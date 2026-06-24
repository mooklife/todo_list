#!/bin/bash
# STS 파일럿 환경 셋업 스크립트
# 대상: Mac (Apple Silicon M1/M2/M3/M4)
# 실행: bash setup.sh

set -e  # 오류 발생 시 즉시 중단

echo "================================================"
echo "  STS 파일럿 환경 셋업"
echo "================================================"

# ── 1. Homebrew 확인 ─────────────────────────────
echo ""
echo "[1/6] Homebrew 확인..."
if ! command -v brew &>/dev/null; then
    echo "  Homebrew 미설치 — 설치 중..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "  ✅ Homebrew 이미 설치됨"
fi

# ── 2. Python 3.11 확인 ──────────────────────────
echo ""
echo "[2/6] Python 3.11 확인..."
if ! command -v python3.11 &>/dev/null; then
    echo "  Python 3.11 설치 중..."
    brew install python@3.11
else
    echo "  ✅ Python 3.11 이미 설치됨: $(python3.11 --version)"
fi

# ── 3. 가상환경 생성 ─────────────────────────────
echo ""
echo "[3/6] 가상환경 생성..."
VENV_DIR="$HOME/sts-pilot-venv"

if [ -d "$VENV_DIR" ]; then
    echo "  ✅ 가상환경 이미 존재: $VENV_DIR"
else
    python3.11 -m venv "$VENV_DIR"
    echo "  ✅ 가상환경 생성: $VENV_DIR"
fi

# 가상환경 활성화
source "$VENV_DIR/bin/activate"
echo "  활성화됨: $VENV_DIR"

# ── 4. pip 업그레이드 + 패키지 설치 ─────────────
echo ""
echo "[4/6] 패키지 설치 중..."
pip install --upgrade pip -q

# PyTorch (Apple Silicon MPS 지원)
echo "  PyTorch 설치 중 (MPS 지원)..."
pip install torch torchvision torchaudio -q

# HuggingFace + 오디오 관련
pip install -r requirements.txt -q
echo "  ✅ 패키지 설치 완료"

# ── 5. HuggingFace 로그인 ────────────────────────
echo ""
echo "[5/6] HuggingFace 로그인 확인..."
echo "  ※ Qwen2.5-Omni 다운로드를 위해 HuggingFace 계정이 필요합니다"
echo "  ※ https://huggingface.co 에서 계정 생성 후 Access Token 발급"
echo ""
echo "  로그인하려면 Enter, 건너뛰려면 Ctrl+C"
read -r
huggingface-cli login

# ── 6. 모델 다운로드 안내 ────────────────────────
echo ""
echo "[6/6] 모델 다운로드 안내..."
echo ""
echo "  파일럿 모델 (3B, ~6GB, 빠른 테스트용):"
echo "    python -c \"from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-Omni-3B')\""
echo ""
echo "  본 모델 (7B, ~15GB, 품질 우선):"
echo "    python -c \"from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-Omni-7B')\""
echo ""

read -p "  3B 파일럿 모델 지금 다운로드하시겠습니까? (y/n): " download_now
if [ "$download_now" = "y" ]; then
    echo "  다운로드 시작 (~6GB, 수 분 소요)..."
    python -c "
from huggingface_hub import snapshot_download
print('다운로드 중...')
path = snapshot_download('Qwen/Qwen2.5-Omni-3B')
print(f'✅ 완료: {path}')
"
fi

# ── 완료 안내 ─────────────────────────────────────
echo ""
echo "================================================"
echo "  ✅ 셋업 완료!"
echo "================================================"
echo ""
echo "  가상환경 활성화:"
echo "    source $VENV_DIR/bin/activate"
echo ""
echo "  테스트 순서:"
echo "    python 01_test_text.py        # 텍스트 기본 동작"
echo "    python 02_test_audio_out.py   # 음성 출력 확인"
echo "    python 03_test_voice_chat.py --record   # STS 핵심 테스트"
echo "    python 04_test_realtime.py    # 실시간 대화"
echo ""
echo "  MPS 동작 확인:"
echo "    python -c \"import torch; print('MPS:', torch.backends.mps.is_available())\""
echo ""
