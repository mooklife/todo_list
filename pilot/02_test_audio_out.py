"""
STEP 2: 텍스트 입력 → 음성 파일 출력
목적: Qwen2.5-Omni의 Talker(TTS) 기능이 동작하는지 확인
결과: output_audio.wav 파일 생성 후 재생
실행: python 02_test_audio_out.py
"""

import torch
import soundfile as sf
import sounddevice as sd
import numpy as np
import time
from pathlib import Path

MODEL_ID = "Qwen/Qwen2.5-Omni-3B"
OUTPUT_FILE = "output_audio.wav"
SAMPLE_RATE = 24000


def load_model():
    from transformers import Qwen2_5OmniModel, Qwen2_5OmniProcessor

    print(f"모델 로딩 중: {MODEL_ID} ...")
    processor = Qwen2_5OmniProcessor.from_pretrained(MODEL_ID)
    model = Qwen2_5OmniModel.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    model.eval()
    print(f"로드 완료 — 디바이스: {next(model.parameters()).device}")
    return model, processor


def text_to_speech(model, processor, text: str) -> np.ndarray:
    """텍스트를 입력받아 음성 numpy 배열 반환"""
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "당신은 친절한 한국어 AI 비서입니다. 자연스럽게 말해주세요."}],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": text}],
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
        output = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            return_audio=True,          # 음성 출력 요청
            use_audio_in_video=False,
        )
    elapsed = time.time() - start

    # 음성 데이터 추출
    if hasattr(output, "audio") and output.audio is not None:
        audio_array = output.audio[0].cpu().numpy().astype(np.float32)
    else:
        # fallback: text output만 있는 경우
        print("  ⚠️  음성 출력 미지원 — 텍스트 응답만 확인 가능")
        audio_array = None

    return audio_array, elapsed


def play_audio(audio_array: np.ndarray, sample_rate: int = SAMPLE_RATE):
    """numpy 배열을 스피커로 재생"""
    print("  ▶ 스피커로 재생 중...")
    sd.play(audio_array, samplerate=sample_rate)
    sd.wait()
    print("  ■ 재생 완료")


def main():
    print("=" * 50)
    print("  STEP 2: 텍스트 → 음성 출력 테스트")
    print("=" * 50)

    model, processor = load_model()

    test_text = "안녕하세요! 저는 여러분의 AI 비서입니다. 무엇을 도와드릴까요?"
    print(f"\n입력 텍스트: {test_text}")

    audio_array, elapsed = text_to_speech(model, processor, test_text)
    print(f"⏱  생성 시간: {elapsed:.2f}초")

    if audio_array is not None:
        # WAV 파일로 저장
        sf.write(OUTPUT_FILE, audio_array, SAMPLE_RATE)
        print(f"💾 음성 파일 저장: {OUTPUT_FILE}")
        print(f"   길이: {len(audio_array) / SAMPLE_RATE:.1f}초")

        # 스피커 재생
        play_audio(audio_array)

        print("\n✅ STEP 2 완료 — 음성 출력 정상")
        print("   다음 단계: python 03_test_voice_chat.py")
    else:
        print("\n❌ 음성 출력 실패 — 모델 버전 또는 설정 확인 필요")


if __name__ == "__main__":
    main()
