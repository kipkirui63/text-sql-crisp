import openai
import os

# Ensure you load the API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

def transcribe_audio(file_path):
    try:
        with open(file_path, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
            return transcript
    except Exception as e:
        print("Transcription error:", str(e))
        return "Transcription failed"
