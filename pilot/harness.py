"""
STS 파일럿 하네스 (구조 검증)

목적:
  파일럿 스크립트(01~04)가 설계(STS_MODEL.MD)에서 정한 "계약"과
  어긋나지 않는지 검증한다. 모델/토치 없이 stdlib만으로 동작하므로
  Windows/Mac/CI 어디서나 실행 가능하다.

검증 항목:
  1) 필수 파일 존재
  2) 각 .py 문법 유효 (컴파일 가능)
  3) 공통 MODEL_ID 일치
  4) 각 파일의 필수 함수 정의 존재
  5) requirements.txt 필수 패키지 포함
  6) STS_MODEL.MD 가 파일럿 파일 목록을 올바르게 참조

실행:
  python pilot/harness.py
  (성공 시 종료코드 0, 실패 시 1)
"""

import ast
import sys
import py_compile
from pathlib import Path

# Windows 콘솔(cp949 등)에서도 유니코드 출력이 깨지거나 죽지 않도록 UTF-8 고정
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── 계약 정의 (Single Source of Truth) ───────────────────────
# 이 값을 바꿀 때는 STS_MODEL.MD 와 CLAUDE.md 도 함께 갱신할 것.

EXPECTED_MODEL_ID = "Qwen/Qwen2.5-Omni-3B"

FILE_CONTRACT = {
    "01_test_text.py": ["load_model", "text_chat", "main"],
    "02_test_audio_out.py": ["load_model", "text_to_speech", "play_audio", "main"],
    "03_test_voice_chat.py": ["load_model", "record_audio", "voice_to_voice", "main"],
    "04_test_realtime.py": ["load_model", "load_vad", "detect_speech", "voice_to_voice", "realtime_loop", "main"],
}

REQUIRED_PACKAGES = [
    "torch", "transformers", "accelerate", "huggingface_hub",
    "sounddevice", "soundfile", "numpy", "scipy", "silero-vad",
]

SUPPORT_FILES = ["requirements.txt", "setup.sh"]

PILOT_DIR = Path(__file__).resolve().parent
REPO_DIR = PILOT_DIR.parent
STS_DOC = REPO_DIR / "STS_MODEL.MD"

# ── 결과 수집 ─────────────────────────────────────────────────
_failures = []
_passes = []


def ok(msg):
    _passes.append(msg)
    print(f"  [PASS] {msg}")


def fail(msg):
    _failures.append(msg)
    print(f"  [FAIL] {msg}")


def section(title):
    print(f"\n[{title}]")


# ── 1) 필수 파일 존재 ─────────────────────────────────────────
def check_files_exist():
    section("1. 필수 파일 존재")
    for name in list(FILE_CONTRACT) + SUPPORT_FILES:
        p = PILOT_DIR / name
        if p.exists():
            ok(f"{name} 존재")
        else:
            fail(f"{name} 없음")


# ── 2) 문법 유효성 ────────────────────────────────────────────
def check_syntax():
    section("2. 파이썬 문법 검증")
    for name in FILE_CONTRACT:
        p = PILOT_DIR / name
        if not p.exists():
            fail(f"{name} 없음 — 문법 검증 건너뜀")
            continue
        try:
            py_compile.compile(str(p), doraise=True)
            ok(f"{name} 문법 정상")
        except py_compile.PyCompileError as e:
            fail(f"{name} 문법 오류: {e}")


# ── 공통: 파일 AST 파싱 ───────────────────────────────────────
def _parse(name):
    p = PILOT_DIR / name
    if not p.exists():
        return None
    try:
        return ast.parse(p.read_text(encoding="utf-8"), filename=name)
    except SyntaxError:
        return None


def _module_functions(tree):
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _module_model_id(tree):
    """모듈 최상위의 MODEL_ID = "..." 할당값 반환 (주석은 제외됨)."""
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "MODEL_ID":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    return None


# ── 3) MODEL_ID 일치 ─────────────────────────────────────────
def check_model_id():
    section("3. 공통 MODEL_ID 일치")
    found = {}
    for name in FILE_CONTRACT:
        tree = _parse(name)
        if tree is None:
            fail(f"{name} 파싱 불가 — MODEL_ID 확인 건너뜀")
            continue
        mid = _module_model_id(tree)
        found[name] = mid
        if mid is None:
            fail(f"{name} 에 MODEL_ID 없음")
        elif mid != EXPECTED_MODEL_ID:
            fail(f"{name} MODEL_ID 불일치: {mid} (기대값 {EXPECTED_MODEL_ID})")
        else:
            ok(f"{name} MODEL_ID = {mid}")

    distinct = {v for v in found.values() if v}
    if len(distinct) > 1:
        fail(f"파일 간 MODEL_ID 불일치: {distinct}")


# ── 4) 필수 함수 존재 ─────────────────────────────────────────
def check_functions():
    section("4. 필수 함수 정의")
    for name, required in FILE_CONTRACT.items():
        tree = _parse(name)
        if tree is None:
            fail(f"{name} 파싱 불가 — 함수 확인 건너뜀")
            continue
        funcs = _module_functions(tree)
        missing = [f for f in required if f not in funcs]
        if missing:
            fail(f"{name} 필수 함수 누락: {missing}")
        else:
            ok(f"{name} 필수 함수 {len(required)}개 모두 존재")


# ── 5) requirements 패키지 ───────────────────────────────────
def check_requirements():
    section("5. requirements.txt 필수 패키지")
    p = PILOT_DIR / "requirements.txt"
    if not p.exists():
        fail("requirements.txt 없음")
        return
    text = p.read_text(encoding="utf-8").lower()
    for pkg in REQUIRED_PACKAGES:
        if pkg.lower() in text:
            ok(f"{pkg} 명시됨")
        else:
            fail(f"{pkg} requirements.txt 에 없음")


# ── 6) 설계 문서 참조 일치 ────────────────────────────────────
def check_design_doc():
    section("6. STS_MODEL.MD 파일럿 참조")
    if not STS_DOC.exists():
        fail("STS_MODEL.MD 없음")
        return
    text = STS_DOC.read_text(encoding="utf-8")
    for name in FILE_CONTRACT:
        if name in text:
            ok(f"설계 문서가 {name} 참조함")
        else:
            fail(f"설계 문서에 {name} 참조 없음 — 동기화 필요")


# ── 메인 ──────────────────────────────────────────────────────
def main():
    print("=" * 56)
    print("  STS 파일럿 하네스 — 구조 검증 (stdlib only)")
    print("=" * 56)

    check_files_exist()
    check_syntax()
    check_model_id()
    check_functions()
    check_requirements()
    check_design_doc()

    print("\n" + "=" * 56)
    total = len(_passes) + len(_failures)
    print(f"  결과: {len(_passes)}/{total} 통과, {len(_failures)} 실패")
    print("=" * 56)

    if _failures:
        print("\n실패 항목:")
        for f in _failures:
            print(f"  - {f}")
        print("\n❌ 하네스 실패 — 파일럿이 설계 계약과 어긋남. CLAUDE.md 참고.")
        return 1

    print("\n✅ 하네스 통과 — 파일럿이 설계 계약과 일치함.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
