import os
import sys

# Available Whisper models
MODELS = {
    "tiny": "39 MB (Fastest, lower accuracy)",
    "base": "142 MB (Default, balanced)",
    "small": "461 MB (Good accuracy, slower)",
    "medium": "1.5 GB (Better accuracy, slow)",
    "large": "3 GB (Best accuracy, very slow)"
}

def download_whisper_model(model_name):
    print(f"\n[INFO] Checking/Downloading model: '{model_name}'...")
    print(f"       Approx. Size: {MODELS.get(model_name, 'Unknown')}")
    try:
        import whisper
        # This will download the model if it's not present in the cache
        model = whisper.load_model(model_name)
        print(f"[OK] Successfully loaded/downloaded model: '{model_name}'")
        return True
    except ImportError:
        print("[ERROR] 'openai-whisper' library is not installed.")
        print("Please run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"[ERROR] An error occurred while downloading '{model_name}': {e}")
        return False

def main():
    print("--- Voice Organizer Model Downloader ---")
    print("This tool helps you pre-download OpenAI Whisper models.")
    print("\nAvailable models:")
    for name, desc in MODELS.items():
        print(f"  - {name:<8} : {desc}")
    
    print("\nThe project currently defaults to using 'base'.")
    print("If you want better accuracy for Chinese, 'small' or 'medium' is recommended.")
    
    while True:
        user_input = input("\nEnter model names to download (separated by space, e.g., 'base small'), or 'q' to quit [default: base]: ").strip().lower()
        
        if user_input == 'q':
            break
        
        if not user_input:
            selected_models = ["base"]
        else:
            selected_models = user_input.split()
        
        # Validate inputs
        valid_models = []
        for m in selected_models:
            if m in MODELS:
                valid_models.append(m)
            else:
                print(f"[WARNING] Unknown model name: '{m}'. Skipping.")
        
        if not valid_models:
            continue
            
        print(f"\nPreparing to download: {', '.join(valid_models)}")
        
        success_count = 0
        for model_name in valid_models:
            if download_whisper_model(model_name):
                success_count += 1
        
        if success_count == len(valid_models):
            print("\n[SUCCESS] All selected models are ready!")
        else:
            print("\n[WARNING] Some models failed to download.")
            
        # Ask if they want to download more
        choice = input("\nDo you want to download other models? (y/n) [n]: ").strip().lower()
        if choice != 'y':
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
