import os
import json
import urllib.request
import urllib.error
from PySide6 import QtCore, QtWidgets

class DownloadWorker(QtCore.QObject):
    finished = QtCore.Signal()
    progress = QtCore.Signal(str) # Message to display

    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir

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
            print(f"Fetching manifest from {manifest_url}")
            with urllib.request.urlopen(manifest_url) as response:
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

        # 3. Download files
        total_files = len(files)
        for index, item in enumerate(files):
            file_url = item.get("url")
            category = item.get("category")
            
            if not file_url or not category:
                continue
                
            # Determine local path
            # Strategy: sounds/random/{category}/{filename}
            filename = file_url.split("/")[-1]
            # Decode URL encoded filename if necessary, but usually simple enough
            
            target_dir = os.path.join(self.base_dir, "sounds", "random", category)
            local_path = os.path.join(target_dir, filename)
            
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            if os.path.exists(local_path):
                # Skip if exists (simple caching)
                continue
                
            self.progress.emit(f"Downloading ({index+1}/{total_files}): {filename}")
            
            try:
                print(f"Downloading {file_url} to {local_path}")
                # Set a timeout for downloads
                urllib.request.urlretrieve(file_url, local_path)
            except Exception as e:
                print(f"Failed to download {file_url}: {e}")
        
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
