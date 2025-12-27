import asyncio
import edge_tts

async def main():
    communicate = edge_tts.Communicate("Hello world", "en-US-AriaNeural")
    await communicate.save("test_audio.mp3")
    print("Saved test_audio.mp3")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
