import os
import shutil
import subprocess
import sys

def main():
    print(">>> Starting Build Process...")
    
    # Project Root is one level up from 'tools'
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dist_dir = os.path.join(project_root, "dist")
    build_dir = os.path.join(project_root, "build")
    
    # Clean previous builds
    if os.path.exists(dist_dir):
        print(f"    Cleaning {dist_dir}...")
        shutil.rmtree(dist_dir)
    if os.path.exists(build_dir):
        print(f"    Cleaning {build_dir}...")
        shutil.rmtree(build_dir)
        
    print(">>> Cleaned old build directories.")
    
    # Check dependencies
    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller", "--version"], stdout=subprocess.DEVNULL)
    except:
        print(">>> PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Build Arguments
    sep = ";" if os.name == 'nt' else ":"
    
    # Assets: Internal
    assets_arg = f"assets{sep}assets"
    # UI: Internal
    ui_arg = f"menu.ui{sep}."
    # Config: Internal (Bundled so users don't modify it)
    config_arg = f"calendar_config.json{sep}."
    
    icon_path = os.path.join(project_root, "assets", "icons", "icon.ico")
    if not os.path.exists(icon_path):
        # Fallback check
        icon_path = os.path.join(project_root, "assets", "icon.ico")
        
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "main.py",
        "--name", "pmpmchan",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--add-data", assets_arg,
        "--add-data", ui_arg,
        "--add-data", config_arg,
    ]
    
    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
    else:
        print("    WARNING: Icon file not found. Building with default icon.")
        
    print(f">>> Running PyInstaller: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=project_root)
    
    print(">>> Build Complete.")
    
    # Post-Build: Copy External Resources
    print(">>> Copying external resources...")
    
    # 1. sounds (Folder)
    src_sounds = os.path.join(project_root, "sounds")
    dst_sounds = os.path.join(dist_dir, "sounds")
    
    if os.path.exists(src_sounds):
        shutil.copytree(src_sounds, dst_sounds)
        print(f"    Copied sounds/")
    else:
        print("    WARNING: 'sounds' directory not found.")

    # 2. calendar_config.json is bundled, NO COPY to dist.
    # Users should not see/edit it.

    # 3. Create a README (Optional but helpful)
    readme_path = os.path.join(dist_dir, "使用说明.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("pmpmchan 分发包\n")
        f.write("=================\n\n")
        f.write("1. pmpmchan.exe: 主程序，双击运行。\n")
        f.write("2. sounds/ 文件夹: 存放语音文件，可自由替换。\n")
        f.write("3. 首次运行会自动下载 cloud 资源（如果有网络）。\n")
        f.write("4. 节日配置已内置，无需修改。\n")
    print(f"    Created 使用说明.txt")

    print("\n>>> All Done! Distribution package is in 'dist/' folder.")

if __name__ == "__main__":
    main()
