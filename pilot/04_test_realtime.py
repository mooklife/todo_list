"""
STEP 4: 마이크 실시간 음성 대화 (VAD 포함)
목적: 말이 끝나면 자동 감지 후 응답하는 실시간 대화 루프 검증
실행: python 04_test_realtime.py
종료: Ctrl+C
"""

import torch
import sounddevice as sd
import soundfile as sf
import numpy as np
import time
import queue
import threading
from collections import deque

MODEL_ID = "Qwen/Qwen2.5-Omni-3B"
SAMPLE_RATE = 16000         # VAD/입력 최적 샘플레이트
OUTPUT_SAMPLE_RATE = 24000  # Qwen TTS 출력 샘플레이트
CHUNK_DURATION = 0.5        # 0.5초 단위로 오디오 수집
SILENCE_THRESHOLD = 1.5     # 침묵 1.5초 후 발화 종료 판단
MAX_RECORD_SECONDS = 10     # 최대 발화 길이

# ── 상담사 페르소나 프롬프트 ──────────────────────────────────
# 서비스용 상세 프롬프트는 추후 별도 작성. 파일럿은 간략 버전.
SYSTEM_PROMPT = (
    "당신은 친절한 전문 상담사입니다. "
    "항상 정중한 존댓말을 사용하고, 한 번에 한 가지씩 간결하게 안내합니다. "
    "답변은 2~3문장 이내로 짧게 말합니다. "
    "모르는 내용은 추측하지 말고, 확인 후 안내드리겠다고 답합니다."
)

# 연결 시 먼저 말할 인사말 (고정 문구)
GREETING_TEXT = "안녕하세요, 무엇이 궁금하신가요?"


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


def load_vad():
    """Silero VAD 로드"""
    import torch
    vad_model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
    )
    (get_speech_timestamps, _, read_audio, *_) = utils
    print("VAD 로드 완료")
    return vad_model, get_speech_timestamps


def detect_speech(vad_model, get_speech_timestamps, audio_array: np.ndarray) -> bool:
    """오디오 배열에서 음성 포함 여부 반환"""
    audio_tensor = torch.FloatTensor(audio_array)
    timestamps = get_speech_timestamps(
        audio_tensor,
        vad_model,
        sampling_rate=SAMPLE_RATE,
        threshold=0.5,
    )
    return len(timestamps) > 0


def speak_text(model, processor, text: str):
    """고정 문구(인사말 등)를 음성으로 합성해 스피커로 재생.
    Omni가 텍스트를 그대로 읽도록 지시. 음성 출력이 없으면 텍스트만 출력."""
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": SYSTEM_PROMPT}],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": f"다음 문장을 토씨 하나 바꾸지 말고 그대로 음성으로만 말하세요: 「{text}」"}],
        },
    ]

    text_input = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=False
    )
    inputs = processor(text=text_input, return_tensors="pt").to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=128,
            do_sample=False,
            return_audio=True,
            use_audio_in_video=False,
        )

    print(f"🗣  상담사: {text}")
    if hasattr(output, "audio") and output.audio is not None:
        audio = output.audio[0].cpu().numpy().astype(np.float32)
        sd.play(audio, samplerate=OUTPUT_SAMPLE_RATE)
        sd.wait()
    else:
        print("  ⚠️  음성 출력 미지원 — 인사말 텍스트만 표시")


def voice_to_voice(model, processor, audio_array: np.ndarray) -> tuple:
    """음성 → 음성 응답"""
    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": SYSTEM_PROMPT}],
        },
        {
            "role": "user",
            "content": [{"type": "audio", "audio": audio_array}],
        },
    ]

    text_input = processor.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=False
    )
    inputs = processor(
        text=text_input,
        audio=audio_array,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            return_audio=True,
            use_audio_in_video=False,
        )

    input_len = inputs["input_ids"].shape[1]
    text_response = processor.decode(
        output.sequences[0][input_len:], skip_special_tokens=True
    )

    audio_response = None
    if hasattr(output, "audio") and output.audio is not None:
        audio_response = output.audio[0].cpu().numpy().astype(np.float32)

    return text_response, audio_response


def realtime_loop(model, processor, vad_model, get_speech_timestamps):
    """실시간 음성 감지 → 응답 루프"""
    chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)
    audio_buffer = []
    silence_chunks = 0
    is_speaking = False

    print("\n" + "=" * 50)
    print("  🎙  실시간 음성 대화 시작")
    print("=" * 50 + "\n")

    # 연결 직후 상담사가 먼저 인사 (마이크 열기 전에 재생 → 인사말 자가 녹음 방지)
    speak_text(model, processor, GREETING_TEXT)

    print("\n  말씀하세요... (종료: Ctrl+C)\n")

    def callback(indata, frames, time_info, status):
        audio_queue.put(indata.copy())

    audio_queue = queue.Queue()

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=chunk_size,
        callback=callback,
    ):
        while True:
            chunk = audio_queue.get().flatten()
            has_speech = detect_speech(vad_model, get_speech_timestamps, chunk)

            if has_speech:
                if not is_speaking:
                    print("🎙  발화 감지...", end="", flush=True)
                    is_speaking = True
                audio_buffer.append(chunk)
                silence_chunks = 0

            elif is_speaking:
                silence_chunks += 1
                audio_buffer.append(chunk)  # 침묵도 버퍼에 포함

                silence_duration = silence_chunks * CHUNK_DURATION
                if silence_duration >= SILENCE_THRESHOLD:
                    # 발화 종료 → 모델 처리
                    print(" 완료")
                    full_audio = np.concatenate(audio_buffer)
                    duration = len(full_audio) / SAMPLE_RATE

                    print(f"🔄 처리 중... (입력: {duration:.1f}초)")
                    start = time.time()
                    text_resp, audio_resp = voice_to_voice(model, processor, full_audio)
                    elapsed = time.time() - start

                    print(f"📝 응답: {text_resp}")
                    print(f"⏱  처리 시간: {elapsed:.2f}초")

                    if audio_resp is not None:
                        print("▶ 재생 중...")
                        sd.play(audio_resp, samplerate=OUTPUT_SAMPLE_RATE)
                        sd.wait()

                    print("\n🎙  다음 발화를 기다리는 중...\n")

                    # 버퍼 초기화
                    audio_buffer = []
                    silence_chunks = 0
                    is_speaking = False

                # 최대 길이 초과 시 강제 처리
                total_duration = len(audio_buffer) * CHUNK_DURATION
                if total_duration >= MAX_RECORD_SECONDS:
                    print(" (최대 길이 도달)")
                    audio_buffer = []
                    silence_chunks = 0
                    is_speaking = False


def main():
    print("=" * 50)
    print("  STEP 4: 실시간 음성 대화 테스트")
    print("=" * 50)

    model, processor = load_model()
    vad_model, get_speech_timestamps = load_vad()

    try:
        realtime_loop(model, processor, vad_model, get_speech_timestamps)
    except KeyboardInterrupt:
        print("\n\n✅ 종료되었습니다.")


if __name__ == "__main__":
    main()
