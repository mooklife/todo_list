"""
STEP 3: 음성 파일 입력 → 음성 응답 (STS 핵심 검증)
목적: 오디오 파일을 입력으로 주고 음성 응답을 받는 End-to-End STS 확인
사전조건: sample_input.wav 파일 필요 (또는 --record 옵션으로 직접 녹음)
실행:
  python 03_test_voice_chat.py                  # sample_input.wav 사용
  python 03_test_voice_chat.py --record         # 5초 직접 녹음 후 테스트
"""

import torch
import soundfile as sf
import sounddevice as sd
import numpy as np
import time
import argparse
from pathlib import Path

MODEL_ID = "Qwen/Qwen2.5-Omni-3B"
SAMPLE_RATE = 24000
RECORD_SECONDS = 5


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
    print(f"로드 완료 — 디바이스: {next(model.parameters()).device}\n")
    return model, processor


def record_audio(seconds: int = RECORD_SECONDS) -> np.ndarray:
    """마이크로 음성 녹음"""
    print(f"🎙  {seconds}초 녹음 시작... (말씀하세요)")
    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32"
    )
    sd.wait()
    print("■ 녹음 완료")
    return audio.flatten()


def voice_to_voice(model, processor, audio_array: np.ndarray) -> tuple:
    """음성 입력 → 모델 처리 → 음성 + 텍스트 응답 반환"""
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "당신은 친절한 한국어 AI 비서입니다. 간결하고 자연스럽게 말해주세요."}],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "audio",
                    "audio": audio_array,    # numpy float32 배열
                }
            ],
        },
    ]

    text_input = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=False
    )
    inputs = processor(
        text=text_input,
        audio=audio_array,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt"
    ).to(model.device)

    start = time.time()
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            return_audio=True,
            use_audio_in_video=False,
        )
    elapsed = time.time() - start

    # 텍스트 응답
    input_len = inputs["input_ids"].shape[1]
    text_response = processor.decode(
        output.sequences[0][input_len:],
        skip_special_tokens=True
    )

    # 음성 응답
    audio_response = None
    if hasattr(output, "audio") and output.audio is not None:
        audio_response = output.audio[0].cpu().numpy().astype(np.float32)

    return text_response, audio_response, elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true", help="마이크로 직접 녹음")
    args = parser.parse_args()

    print("=" * 50)
    print("  STEP 3: 음성 입력 → 음성 응답 (STS 핵심)")
    print("=" * 50)

    model, processor = load_model()

    # 오디오 입력 준비
    if args.record:
        audio_input = record_audio(RECORD_SECONDS)
        sf.write("sample_input.wav", audio_input, SAMPLE_RATE)
        print("📁 녹음 저장: sample_input.wav")
    else:
        input_file = Path("sample_input.wav")
        if not input_file.exists():
            print("⚠️  sample_input.wav 파일 없음")
            print("   --record 옵션으로 실행하거나 sample_input.wav 파일을 준비하세요")
            print("   예: python 03_test_voice_chat.py --record")
            return

        audio_input, sr = sf.read(str(input_file), dtype="float32")
        if audio_input.ndim > 1:
            audio_input = audio_input[:, 0]  # 모노 변환
        print(f"📂 입력 파일: {input_file} ({len(audio_input)/sr:.1f}초)")

    # STS 처리
    print("\n🔄 Qwen2.5-Omni 처리 중...")
    text_response, audio_response, elapsed = voice_to_voice(model, processor, audio_input)

    print(f"\n📝 텍스트 응답: {text_response}")
    print(f"⏱  처리 시간: {elapsed:.2f}초")

    if audio_response is not None:
        output_file = "output_response.wav"
        sf.write(output_file, audio_response, SAMPLE_RATE)
        print(f"💾 음성 응답 저장: {output_file}")

        print("\n▶ 응답 재생 중...")
        sd.play(audio_response, samplerate=SAMPLE_RATE)
        sd.wait()

        print("\n✅ STEP 3 완료 — End-to-End STS 동작 확인!")
        print(f"   지연 시간: {elapsed:.2f}초")
        print("   다음 단계: python 04_test_realtime.py")
    else:
        print("\n⚠️  음성 응답 없음 — 텍스트 응답만 확인됨")
        print("   모델 버전 또는 return_audio 파라미터 확인 필요")


if __name__ == "__main__":
    main()
