import os
import threading
import time
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool

class TranscriptionWorker(QRunnable):
    def __init__(self, file_path, config, callback):
        super().__init__()
        self.file_path = file_path
        self.config = config
        self.callback = callback

    def run(self):
        try:
            # Simulate processing time or real processing
            # In real implementation, this would import whisper and run it
            text = Transcriber.transcribe_file(self.file_path, self.config)
            self.callback(self.file_path, text)
        except Exception as e:
            self.callback(self.file_path, f"Error: {str(e)}")

class Transcriber(QObject):
    _instance = None
    _model = None
    _model_lock = threading.Lock() # Lock for model loading
    _inference_lock = threading.Lock() # Lock for model inference
    _has_whisper = False
    _has_ffmpeg = False
    
    # Signals must be on a QObject
    transcription_finished = Signal(str, str) # file_path, text

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Transcriber, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        super().__init__()
        self._initialized = True
        self.thread_pool = QThreadPool()
        self.check_whisper_availability()

    def check_whisper_availability(self):
        try:
            import whisper
            self._has_whisper = True
            
            # Check for ffmpeg
            import shutil
            if shutil.which("ffmpeg"):
                self._has_ffmpeg = True
                print("Whisper and ffmpeg are available.")
            else:
                self._has_ffmpeg = False
                print("Whisper is installed but ffmpeg is MISSING.")
                
        except ImportError:
            self._has_whisper = False
            self._has_ffmpeg = False
            print("Whisper is NOT installed.")

    def load_model(self, model_size="small"):
        if not self._has_whisper:
            return
        if not self._has_ffmpeg:
            print("Cannot load model: ffmpeg is missing.")
            return

        with self._model_lock:
            if self._model is None:
                import whisper
                print(f"Loading Whisper model: {model_size}...")
                try:
                    self._model = whisper.load_model(model_size)
                    print("Whisper model loaded.")
                except Exception as e:
                    print(f"Failed to load Whisper model: {e}")
                    self._model = None

    def start_transcription(self, file_path, partial=True, language="auto"):
        worker = TranscriptionWorker(
            file_path, 
            {"partial": partial, "language": language}, 
            self._on_worker_finished
        )
        self.thread_pool.start(worker)

    def _on_worker_finished(self, file_path, text):
        self.transcription_finished.emit(file_path, text)

    @staticmethod
    def transcribe_file(file_path, config):
        """
        Static method to perform the actual transcription (blocking).
        """
        partial = config.get("partial", True)
        language = config.get("language", "auto")
        
        # 1. Try Real Whisper
        try:
            import whisper
            # We need to access the singleton's model, but this static method runs in a worker thread.
            instance = Transcriber._instance
            
            if instance:
                if not instance._has_ffmpeg:
                    return "【错误】未检测到 ffmpeg，无法识别。请安装 ffmpeg。"
                
                # Auto-load model if not loaded (Thread-safe check)
                if instance._model is None:
                    instance.load_model()
                
                # Double check after potential load
                if instance._model is None:
                    return "【错误】模型加载失败，请检查控制台日志。"

                # Real transcription logic
                # Load audio first to handle partial transcription
                audio = whisper.load_audio(file_path)
                
                if partial:
                    # Take first 30 seconds (16kHz sample rate)
                    # 30 * 16000 = 480000 samples
                    max_samples = 30 * 16000
                    if len(audio) > max_samples:
                        audio = audio[:max_samples]
                
                # Configure options based on language
                options = {"fp16": False}
                
                if language == "zh":
                    options["language"] = "zh"
                    options["initial_prompt"] = "以下是普通话录音，请用简体中文转录。"
                elif language == "ja":
                    options["language"] = "ja"
                    options["initial_prompt"] = "以下は日本語の音声です。"
                elif language == "en":
                    options["language"] = "en"
                    options["initial_prompt"] = "The following is English audio."
                else:
                    # Auto detect
                    options["initial_prompt"] = "Transcribe the following audio."

                # Transcribe
                # Serialize inference to avoid race conditions on the single model instance
                with instance._inference_lock:
                    result = instance._model.transcribe(audio, **options) 
                
                text = result["text"].strip()
                return text
        except ImportError:
            return "【错误】缺少依赖库 (Whisper/Torch)。"
        except Exception as e:
            print(f"Whisper failed: {e}")
            return f"【错误】识别出错: {str(e)}"

        # 2. Fallback / Mock Logic (Should not be reached if instance exists and ffmpeg is there)
        # But if for some reason we fell through without error...
        return "【未知错误】无法执行识别。"
