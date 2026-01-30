import os
import shutil
import subprocess
import sys


def run_command(command):
    print(f"[INFO] Running: {' '.join(command)}")
    try:
        subprocess.check_call(" ".join(command), shell=True)
        return True
    except subprocess.CalledProcessError:
        print(f"[ERROR] Command failed: {' '.join(command)}")
        return False


def main():
    print("Starting Voice Organizer build process...")

    # 1. Check / install PyInstaller
    try:
        import PyInstaller  # noqa: F401
        print("[INFO] PyInstaller is already installed.")
    except ImportError:
        print("[INFO] PyInstaller not found. Installing...")
        if not run_command([sys.executable, "-m", "pip", "install", "pyinstaller"]):
            return

    # 2. Clean previous build artifacts for this tool
    for folder in ["dist_voice_organizer", "build_voice_organizer"]:
        if os.path.exists(folder):
            print(f"[INFO] Cleaning {folder} directory...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"[WARNING] Failed to clean {folder}: {e}")

    # 3. Run PyInstaller
    print("[INFO] Running PyInstaller for Voice Organizer...")

    # We build a single-file exe without bundling models.
    # Assets / sounds will be copied as external folders.
    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--name",
        "voice_organizer",
        "tools/voice_organizer.py",
    ]

    if not run_command(pyinstaller_cmd):
        print("[ERROR] Voice Organizer build failed.")
        return

    # 4. Prepare output folder
    print("[INFO] Preparing output folder...")
    src_dist = os.path.join("dist", "voice_organizer")
    if not os.path.exists(src_dist):
        print("[ERROR] Expected dist/voice_organizer folder not found.")
        return

    dest_dir = "dist_voice_organizer"
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.copytree(src_dist, dest_dir)

    # 5. Copy Voice Organizer setup guide if present
    setup_doc = os.path.join("tools", "VOICE_ORGANIZER_SETUP.md")
    if os.path.exists(setup_doc):
        shutil.copy(setup_doc, os.path.join(dest_dir, "VOICE_ORGANIZER_SETUP.md"))

    print("-" * 40)
    print("[SUCCESS] Voice Organizer build completed!")
    print(f"[INFO] Executable located at: {os.path.join(dest_dir, 'voice_organizer.exe')}")
    print("[INFO] Whisper 模型不会打包在 exe 中，仍然走本地缓存 (~/.cache/whisper)。")
    print("-" * 40)


if __name__ == "__main__":
    main()

