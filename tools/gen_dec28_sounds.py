import asyncio
import os
import edge_tts

# Voice configuration
VOICE = "en-US-AriaNeural"

SOUNDS = {
    "start": ["Happy December 28th! Let's start working on this special day."],
    "end": ["Happy December 28th! Work is done for this date."],
    "interval": ["Happy December 28th! Taking a break on the 28th."],
    "resume": ["Happy December 28th! Back to work."],
    "exit": ["Happy December 28th! See you next year."]
}

async def generate():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cloud_dir = os.path.join(base_dir, "cloud")
    
    print(f"Generating Dec 28 sounds to: {cloud_dir}")
    
    for category, sentences in SOUNDS.items():
        # Target: cloud/{category}/dec28/
        target_dir = os.path.join(cloud_dir, category, "dec28")
        os.makedirs(target_dir, exist_ok=True)
        
        for i, text in enumerate(sentences, 1):
            filename = f"{i}.mp3"
            full_path = os.path.join(target_dir, filename)
            print(f"Generating {category}/dec28/{filename}: {text}")
            try:
                communicate = edge_tts.Communicate(text, VOICE)
                await communicate.save(full_path)
            except Exception as e:
                print(f"Error generating {full_path}: {e}")

if __name__ == "__main__":
    asyncio.run(generate())
