import os
import urllib.request
import urllib.error
import threading
from PySide6 import QtCore, QtWidgets

# 配置云端资源的基础URL (请修改为您自己的服务器地址)
# Configure the base URL for cloud resources (Please change to your own server address)
CLOUD_BASE_URL = "https://example.com/pomodoro_assets/"

# 必需的资源列表
# List of required resources
REQUIRED_RESOURCES = [
    # 仅下载音频资源
    "sounds/start.mp3",
    "sounds/end.mp3",
    "sounds/rest_start.mp3",
]

# 添加数字资源
# Add digit resources
# for i in range(10):
#    REQUIRED_RESOURCES.append(f"assets/digits/{i}.png")
# REQUIRED_RESOURCES.append("assets/digits/colon.png")

class DownloadWorker(QtCore.QObject):
    finished = QtCore.Signal()
    progress = QtCore.Signal(str) # 这里的 str 是当前正在下载的文件名

    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir

    def run(self):
        # 检查是否配置了有效的 URL
        if "example.com" in CLOUD_BASE_URL:
            print("Warning: CLOUD_BASE_URL is not configured. Skipping download.")
            self.finished.emit()
            return

        parent_dir = os.path.dirname(self.base_dir)
        
        # 检查并创建必要的目录
        # Check and create necessary directories
        dirs_to_check = [
            os.path.join(self.base_dir, "assets"),
            os.path.join(self.base_dir, "assets", "digits"),
            os.path.join(self.base_dir, "sounds"),
        ]
        for d in dirs_to_check:
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)

        for rel_path in REQUIRED_RESOURCES:
            local_path = os.path.join(self.base_dir, rel_path)
            
            # 检查上一级目录是否存在资源 (开发环境兼容)
            # Check parent directory for resources (dev environment compatibility)
            parent_path = os.path.join(parent_dir, rel_path)
            
            if os.path.exists(local_path) or os.path.exists(parent_path):
                continue

            # 下载资源
            # Download resource
            url = CLOUD_BASE_URL + rel_path.replace("\\", "/")
            self.progress.emit(f"Downloading {rel_path}...")
            try:
                # 确保目标目录存在
                target_dir = os.path.dirname(local_path)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                    
                print(f"Downloading {url} to {local_path}")
                urllib.request.urlretrieve(url, local_path)
            except Exception as e:
                print(f"Failed to download {url}: {e}")
        
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
