import os
import shutil
import subprocess
import sys

def run_command(command):
    print(f"[INFO] Running: {' '.join(command)}")
    try:
        subprocess.check_call(command, shell=True)
        return True
    except subprocess.CalledProcessError:
        print(f"[ERROR] Command failed: {' '.join(command)}")
        return False

def main():
    print("Starting build process...")
    
    # 1. Check/Install PyInstaller
    try:
        import PyInstaller
        print("[INFO] PyInstaller is already installed.")
    except ImportError:
        print("[INFO] PyInstaller not found. Installing...")
        if not run_command([sys.executable, "-m", "pip", "install", "pyinstaller"]):
            return

    # 2. Clean previous build
    for folder in ["dist", "build"]:
        if os.path.exists(folder):
            print(f"[INFO] Cleaning {folder} directory...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"[WARNING] Failed to clean {folder}: {e}")

    # 3. Run PyInstaller
    print("[INFO] Running PyInstaller...")
    # Use the current python executable to run pyinstaller module
    if not run_command([sys.executable, "-m", "PyInstaller", "main.spec"]):
        print("[ERROR] Build failed.")
        return

    # 4. Copy documentation
    print("[INFO] Copying documentation...")
    dest_dir = os.path.join("dist", "PomodoroWidget")
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    
    # 优先复制 README.md 作为用户的使用说明
    if os.path.exists("README.md"):
        shutil.copy("README.md", os.path.join(dest_dir, "使用说明.md"))
    elif os.path.exists("FOLDER_STRUCTURE.md"):
         # Fallback
        shutil.copy("FOLDER_STRUCTURE.md", os.path.join(dest_dir, "文件夹结构说明.md"))

    print("-" * 40)
    print("[SUCCESS] Build completed successfully!")
    print(f"[INFO] Executable located at: {os.path.join('dist', 'PomodoroWidget', 'PomodoroWidget.exe')}")
    print("-" * 40)

if __name__ == "__main__":
    main()
