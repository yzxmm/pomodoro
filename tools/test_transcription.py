import os
import sys
import time
from transcriber import Transcriber

def test_callback(file_path, text):
    print(f"\n[Callback] File: {file_path}")
    print(f"[Callback] Text: {text}")

def main():
    print("Testing Transcriber...")
    
    # Check singleton
    t = Transcriber()
    print(f"Whisper available: {t._has_whisper}")
    print(f"FFmpeg available: {t._has_ffmpeg}")
    
    if not t._has_whisper or not t._has_ffmpeg:
        print("Environment not ready.")
        return

    # Find a wav file to test
    target_file = None
    folder = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to root
    root = os.path.dirname(folder)
    
    # Try to find any audio file in root or subdirs
    for root_dir, dirs, files in os.walk(root):
        for f in files:
            if f.endswith(('.wav', '.mp3')):
                target_file = os.path.join(root_dir, f)
                break
        if target_file: break
    
    if not target_file:
        print("No audio file found for testing.")
        # Create a dummy one? No, we need real audio for real test, 
        # but for now let's just use the generate_valid_wav tool if needed.
        # Assuming generate_valid_wav.py exists, let's run it.
        try:
            import generate_valid_wav
            target_file = os.path.join(folder, "test_audio_440.wav")
            generate_valid_wav.generate_tone(target_file)
            print(f"Generated test file: {target_file}")
        except ImportError:
            print("Cannot generate test file.")
            return

    print(f"Transcribing file: {target_file}")
    
    # Test blocking method directly first
    try:
        print("Loading model...")
        t.load_model()
        print("Model loaded. Starting transcription...")
        
        # Manually call static method config
        config = {"partial": True, "language": "en"} # Use English for tone? Or auto.
        
        # Call the static method directly to see errors
        text = Transcriber.transcribe_file(target_file, config)
        print(f"Direct Transcription Result: {text}")
        
    except Exception as e:
        print(f"Direct transcription failed: {e}")

if __name__ == "__main__":
    main()