"""Generate German audio fixtures from text files using gTTS."""
import os
from pathlib import Path
from gtts import gTTS

FIXTURES = Path(__file__).parent / "fixtures"

TASKS = ["veggie_answer", "saying_answer", "picture_answer"]


def generate():
    for task in TASKS:
        txt_path = FIXTURES / f"{task}.txt"
        mp3_path = FIXTURES / f"{task}.mp3"

        if mp3_path.exists():
            print(f"  SKIP  {mp3_path.name} (already exists)")
            continue

        text = txt_path.read_text(encoding="utf-8").strip()
        print(f"  GEN   {mp3_path.name} ({len(text)} chars)")
        tts = gTTS(text=text, lang="de", slow=False)
        tts.save(str(mp3_path))
        print(f"  OK    {mp3_path.name} ({mp3_path.stat().st_size} bytes)")


if __name__ == "__main__":
    generate()
