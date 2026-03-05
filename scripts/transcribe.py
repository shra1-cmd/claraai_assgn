import whisper
import sys
from pathlib import Path

model = whisper.load_model("base")   # small and fast

def transcribe_audio(audio_path, output_path):
    result = model.transcribe(audio_path)

    with open(output_path, "w") as f:
        f.write(result["text"])

    print(f"Transcript saved to {output_path}")


if __name__ == "__main__":
    audio_file = sys.argv[1]
    output_file = sys.argv[2]

    transcribe_audio(audio_file, output_file)