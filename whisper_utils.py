import os
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

client = OpenAI()

def transcribe_audio(filepath):
    try:
        with open(filepath, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Transcription error: {e}")
        return "Transcription failed"
