"""
STEP 1: 텍스트 입력 → 텍스트 출력
목적: Qwen2.5-Omni 모델이 로컬에서 정상 동작하는지 기본 확인
실행: python 01_test_text.py
"""

import torch
import time

# ── 모델 설정 ────────────────────────────────────────────────
# 파일럿은 3B (가벼움, 빠른 다운로드) → 검증 후 7B로 교체
MODEL_ID = "Qwen/Qwen2.5-Omni-3B"
# MODEL_ID = "Qwen/Qwen2.5-Omni-7B"  # 품질 우선 시 교체


def load_model():
    from transformers import Qwen2_5OmniModel, Qwen2_5OmniProcessor

    print(f"[1/2] 모델 로딩 중: {MODEL_ID}")
    print("      (최초 실행 시 HuggingFace에서 다운로드, 수 분 소요)")

    processor = Qwen2_5OmniProcessor.from_pretrained(MODEL_ID)

    model = Qwen2_5OmniModel.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",          # MPS (Apple Silicon) 자동 감지
    )
    model.eval()

    # 사용 중인 디바이스 출력
    device = next(model.parameters()).device
    print(f"[2/2] 모델 로드 완료 — 디바이스: {device}")
    return model, processor


def text_chat(model, processor, user_text: str) -> str:
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "당신은 친절한 한국어 AI 비서입니다. 간결하게 답변하세요."}],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": user_text}],
        },
    ]

    text_input = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=False
    )
    inputs = processor(text=text_input, return_tensors="pt").to(model.device)

    start = time.time()
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            use_audio_in_video=False,
        )
    elapsed = time.time() - start

    # 입력 토큰 제거 후 응답만 디코딩
    input_len = inputs["input_ids"].shape[1]
    response = processor.decode(
        output_ids[0][input_len:],
        skip_special_tokens=True
    )
    return response, elapsed


def main():
    print("=" * 50)
    print("  STEP 1: 텍스트 기본 동작 테스트")
    print("=" * 50)

    model, processor = load_model()

    test_questions = [
        "안녕하세요! 자기소개 해줘.",
        "오늘 날씨가 어떨 것 같아?",
        "파이썬에서 리스트 정렬하는 방법은?",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n[테스트 {i}] 질문: {question}")
        response, elapsed = text_chat(model, processor, question)
        print(f"  응답: {response}")
        print(f"  ⏱  응답 시간: {elapsed:.2f}초")

    print("\n✅ STEP 1 완료 — 텍스트 기본 동작 정상")
    print("   다음 단계: python 02_test_audio_out.py")


if __name__ == "__main__":
    main()
