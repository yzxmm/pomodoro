import os
import json
import urllib.request
import urllib.error
import concurrent.futures
from PySide6 import QtCore, QtWidgets

class DownloadWorker(QtCore.QObject):
    finished = QtCore.Signal()
    progress = QtCore.Signal(str) # Message to display

    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir

    def download_file(self, item, index, total_files):
        file_url = item.get("url")
        category = item.get("category")
        
        if not file_url or not category:
            return
            
        # Determine local path
        filename = file_url.split("/")[-1]
        
        # Determine target directory based on category and metadata (season/tags)
        # User requested separation: cloud downloads go to 'cloud' (outside sounds folder to avoid packaging)
        # Logic mirrors local structure: category/season or category/tags/tag
        
        target_base = os.path.join(self.base_dir, "cloud", category)
        
        season = (item.get('season') or '').strip().lower()
        tag = (item.get('tag') or '').strip().lower()
        
        if season:
            target_dir = os.path.join(target_base, season)
        elif tag:
            target_dir = os.path.join(target_base, 'tags', tag)
        else:
            target_dir = target_base

        local_path = os.path.join(target_dir, filename)
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        
        if os.path.exists(local_path):
            # Check if file size matches (basic verification)
            # If server doesn't provide size, we might just trust local if > 0 bytes
            if os.path.getsize(local_path) > 0:
                return

        # Emit progress (thread-safe because signals are thread-safe in Qt)
        # However, calling emit from a thread different from the one QObject lives in 
        # is queued, which is fine.
        # But we want to avoid spamming.
        self.progress.emit(f"Downloading: {filename}")
        
        try:
            # Use a faster mirror if available
            # Replace github raw with a mirror like moeyy.cn or others if acceptable
            # mirror_url = file_url.replace("raw.githubusercontent.com", "raw.gitmirror.com")
            # For now, let's just stick to original but maybe increase timeout?
            
            print(f"Downloading {file_url} to {local_path}")
            
            # Use urlopen with timeout to fail fast on stuck connections
            # and a larger buffer size? 
            # urlretrieve is simple but blocking and basic.
            # Let's use requests-like manual download for better control?
            # Or just set global timeout.
            
            import socket
            socket.setdefaulttimeout(10) # 10 seconds timeout
            
            # Simple retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    urllib.request.urlretrieve(file_url, local_path)
                    break # Success
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    print(f"Retry {attempt+1}/{max_retries} for {filename}")
                    
        except Exception as e:
            print(f"Failed to download {file_url}: {e}")

    def run(self):
        settings_path = os.path.join(self.base_dir, "settings.json")
        manifest_url = ""
        
        # 1. Load settings to get manifest URL
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    manifest_url = settings.get("sounds_update_url", "")
            except Exception as e:
                print(f"Error reading settings: {e}")

        if not manifest_url:
            print("No sounds_update_url found in settings.json")
            self.finished.emit()
            return

        # self.progress.emit("Checking for updates...")
        self.progress.emit("Moe moe kyunkyunnnnnnn↝")
        
        # Special handling for git repositories
        if manifest_url.endswith('.git'):
            self.progress.emit("Syncing with git repository...")
            cloud_dir = os.path.join(self.base_dir, "cloud")
            
            try:
                import subprocess
                import shutil
                
                # Check if git is available
                try:
                    subprocess.check_call(['git', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print("Git is available.")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("Git is not installed or not in PATH")
                    self.progress.emit("Git not found, skipping update")
                    self.finished.emit()
                    return

                if os.path.isdir(os.path.join(cloud_dir, '.git')):
                    # It's already a git repo, pull
                    print(f"Pulling in {cloud_dir}")
                    # self.progress.emit("Updating existing repository...")
                    self.progress.emit("Moe moe kyunkyunnnnnnn↝")
                    try:
                        # 1. Get list of deleted files (User deleted them because they didn't like them)
                        status_out = subprocess.check_output(['git', 'status', '--porcelain'], cwd=cloud_dir).decode('utf-8', errors='ignore')
                        deleted_files = []
                        for line in status_out.splitlines():
                            # Format: " D path/to/file" or "D  path/to/file"
                            if line.strip().startswith('D '):
                                path = line.strip()[2:].strip()
                                if path.startswith('"') and path.endswith('"'):
                                    path = path[1:-1]
                                deleted_files.append(path)
                        
                        # 2. Revert local changes to ensure pull succeeds (restore deleted files temporarily)
                        subprocess.check_call(['git', 'checkout', '.'], cwd=cloud_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        # 3. Get old HEAD to compare later
                        old_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cloud_dir).decode('utf-8').strip()
                        
                        # 4. Pull updates
                        subprocess.check_call(['git', 'pull'], cwd=cloud_dir)
                        
                        # 5. Get new HEAD
                        new_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cloud_dir).decode('utf-8').strip()
                        
                        # 6. Re-delete files that were NOT updated in this pull
                        if old_head != new_head:
                            # Get list of files changed in this update
                            diff_out = subprocess.check_output(['git', 'diff', '--name-only', old_head, new_head], cwd=cloud_dir).decode('utf-8', errors='ignore')
                            updated_files = set(line.strip() for line in diff_out.splitlines())
                            
                            for f_rel in deleted_files:
                                # Git paths use forward slash, check if it's in updated_files
                                if f_rel not in updated_files:
                                    # Not updated, so user still doesn't want it -> delete again
                                    full_path = os.path.join(cloud_dir, f_rel)
                                    if os.path.exists(full_path):
                                        print(f"Re-deleting unchanged file: {f_rel}")
                                        os.remove(full_path)
                                else:
                                    print(f"Restoring updated file: {f_rel}")
                        else:
                            # No updates at all, re-delete everything user had deleted
                            for f_rel in deleted_files:
                                full_path = os.path.join(cloud_dir, f_rel)
                                if os.path.exists(full_path):
                                    os.remove(full_path)

                    except subprocess.CalledProcessError as e:
                        print(f"Git pull failed: {e}")
                        self.progress.emit("Git pull failed")
                else:
                    # Not a git repo or doesn't exist
                    if os.path.exists(cloud_dir):
                        # Check if empty
                        if os.listdir(cloud_dir):
                            print(f"Directory {cloud_dir} exists and is not empty. Backing up...")
                            self.progress.emit("Backing up old cloud folder...")
                            backup_path = cloud_dir + "_backup"
                            try:
                                if os.path.exists(backup_path):
                                    shutil.rmtree(backup_path)
                                os.rename(cloud_dir, backup_path)
                            except OSError as e:
                                print(f"Backup failed (files might be in use): {e}")
                                self.progress.emit("Backup failed: Close folder!")
                                raise Exception(f"Could not backup {cloud_dir}. Please ensure it is not open in any terminal or explorer.")
                        else:
                            # Empty directory, safe to remove so clone works or just clone into it (git clone works on empty dir?)
                            # Standard git clone works if dir is empty.
                            pass
                    
                    print(f"Cloning {manifest_url} to {cloud_dir}")
                    self.progress.emit("Cloning repository...")
                    subprocess.check_call(['git', 'clone', manifest_url, cloud_dir])
                    
            except Exception as e:
                print(f"Git operation failed: {e}")
                self.progress.emit(f"Git failed: {e}")
            
            # After Git Sync: NO COPY needed as main.py now scans cloud dir directly
            # This prevents duplicate files (one in cloud, one in sounds)
            self.finished.emit()
            return

        # 2. Download manifest
        try:
            # Use mirror for manifest too if possible, but let's stick to reliable source first
            print(f"Fetching manifest from {manifest_url}")
            with urllib.request.urlopen(manifest_url, timeout=10) as response:
                data = response.read()
                manifest = json.loads(data)
        except Exception as e:
            print(f"Failed to fetch manifest: {e}")
            self.finished.emit()
            return

        files = manifest.get("files", [])
        if not files:
            print("No files found in manifest")
            self.finished.emit()
            return

        # 3. Download files in parallel
        total_files = len(files)
        # Increase workers significantly since IO bound
        max_workers = 20  
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for index, item in enumerate(files):
                futures.append(executor.submit(self.download_file, item, index, total_files))
            
            # Wait for all to complete
            concurrent.futures.wait(futures)
        
        self.finished.emit()

class DownloadManager(QtWidgets.QWidget):
    download_complete = QtCore.Signal()

    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir
        self.worker = DownloadWorker(base_dir)
        self.thread = QtCore.QThread()
        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_finished)
        
        # 简单的进度显示 (可选)
        # Simple progress display (optional)
        self.setWindowTitle("Updating Resources...")
        self.resize(300, 100)
        self.label = QtWidgets.QLabel("Moe moe kyunkyunnnnnnn↝", self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        
        self.worker.progress.connect(self.label.setText)

    def start(self):
        self.show()
        self.thread.start()

    def on_finished(self):
        self.close()
        self.download_complete.emit()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    manager = DownloadManager(os.path.dirname(os.path.abspath(__file__)))
    manager.download_complete.connect(app.quit)
    manager.start()
    sys.exit(app.exec())
