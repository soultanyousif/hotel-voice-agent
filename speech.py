

import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv(override=True)

if not os.environ.get("GROQ_API_KEY"):
    raise RuntimeError(
        "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys, "
        "then put it in a .env file (see .env.example) or set it as an HF Space secret."
    )

client = Groq()

ASR_MODEL = "whisper-large-v3"

TTS_MODEL = "canopylabs/orpheus-arabic-saudi"
TTS_VOICE = "sultan"  # other male options: "fahad", "abdullah"
TTS_MAX_CHARS = 190  # < 200 

OUTPUT_DIR = Path(__file__).parent / "tts_out"
OUTPUT_DIR.mkdir(exist_ok=True)


def transcribe_audio(audio_path):
    """Transcribe a guest's spoken turn to Arabic text, via Groq's whisper-large-v3."""
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=ASR_MODEL,
            language="ar",
        )
    return transcription.text.strip()


def synthesize_speech(text):
    """Synthesize the agent's reply as Najdi-accented speech, via Groq's
    hosted Orpheus Arabic Saudi model.

    Returns the path to the generated wav file.
    """
    if len(text) > TTS_MAX_CHARS:
        text = text[:TTS_MAX_CHARS].rsplit(" ", 1)[0]

    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="wav",
    )

    import uuid
    output_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.wav"
    response.write_to_file(str(output_path))
    return str(output_path)