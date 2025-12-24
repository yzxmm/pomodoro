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
        target_dir = os.path.join(self.base_dir, "sounds", "random", category)
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

        self.progress.emit("Checking for updates...")
        
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
        self.label = QtWidgets.QLabel("Checking resources...", self)
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
