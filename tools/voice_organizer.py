import sys
import os
import shutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QFileSystemModel, QLabel, QPushButton, QFileDialog, QSplitter, 
                               QHeaderView, QMenu, QMessageBox, QAbstractItemView,
                               QToolBar, QStyle, QComboBox)
from PySide6.QtCore import QDir, Qt, QSettings, QModelIndex, QUrl
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QIcon
from PySide6.QtMultimedia import QMediaPlayer

# Import components
from voice_components import (MockTranscriptionFileSystemModel, SubtitleDelegate, 
                              DraggableTreeView, DraggableColumnView, MOCK_TEXTS, AudioController)
from transcriber import Transcriber

class VoiceOrganizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("~让音频回它该在的地方去！~")
        self.resize(1200, 800)
        self.setAcceptDrops(True)
        
        # Audio Player
        self.audio_controller = AudioController(self)
        self.audio_controller.player.mediaStatusChanged.connect(self.handle_media_status)
        
        # Transcriber
        self.transcriber = Transcriber()
        self.transcriber.transcription_finished.connect(self.on_transcription_finished)

        self.setup_ui()
        self.undo_stack = [] # Undo stack
        self.load_settings()

    def handle_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.stop_audio()
            self.lbl_now_playing.setText("Finished")

    def on_transcription_finished(self, file_path, text):
        print(f"Transcription finished for {file_path}: {text[:50]}...")
        self.file_model.update_transcription(file_path, text)
        self.statusBar().showMessage(f"已识别: {os.path.basename(file_path)}", 3000)

    def setup_ui(self):
        # Center window
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # Toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        # Play/Stop Actions
        self.action_play = QAction(self.style().standardIcon(QStyle.SP_MediaPlay), "播放 (Play)", self)
        self.action_play.triggered.connect(self.play_selected_file)
        self.toolbar.addAction(self.action_play)

        self.action_stop = QAction(self.style().standardIcon(QStyle.SP_MediaStop), "停止 (Stop)", self)
        self.action_stop.triggered.connect(self.stop_audio)
        self.action_stop.setEnabled(False)
        self.toolbar.addAction(self.action_stop)
        
        self.toolbar.addSeparator()
        
        # Language Selector
        self.combo_language = QComboBox()
        self.combo_language.addItems(["自动 (Auto)", "中文 (Chinese)", "日语 (Japanese)", "英语 (English)"])
        self.combo_language.setToolTip("选择识别语言")
        self.toolbar.addWidget(self.combo_language)
        
        self.lbl_now_playing = QLabel("Ready")
        self.lbl_now_playing.setStyleSheet("color: gray; margin-left: 10px;")
        self.toolbar.addWidget(self.lbl_now_playing)

        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)

        # Left Panel (Source)
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Source Directory Selection
        self.src_dir_layout = QHBoxLayout()
        self.btn_select_src = QPushButton("选择源文件夹 (Source)")
        self.btn_select_src.clicked.connect(self.select_source_directory)
        self.lbl_src_path = QLabel("请选择录音文件夹...")
        self.src_dir_layout.addWidget(self.btn_select_src)
        
        self.src_dir_layout.addWidget(self.lbl_src_path)
        self.left_layout.addLayout(self.src_dir_layout)
        
        # REMOVED UNDO BUTTON as requested

        # File List
        self.file_list = DraggableTreeView()
        self.file_list.setStyleSheet("QTreeView::item { padding: 5px; height: 30px; }")
        self.file_model = MockTranscriptionFileSystemModel()
        self.file_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot) 
        self.file_model.setNameFilters(["*.wav", "*.mp3", "*.flac", "*.m4a"])
        self.file_model.setNameFilterDisables(False)
        self.file_model.setReadOnly(False)
        
        self.file_list.setModel(self.file_model)
        self.file_list.setRootIndex(self.file_model.setRootPath("")) 
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # Enable double click to play
        self.file_list.doubleClicked.connect(self.play_selected_file)

        self.file_list.setDragEnabled(True)
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self.show_context_menu)
        self.file_list.setColumnWidth(0, 400)
        
        self.subtitle_delegate = SubtitleDelegate(self.file_model, self.file_list)
        self.file_list.setItemDelegateForColumn(0, self.subtitle_delegate)
        self.file_list.setColumnHidden(4, True) 
        
        self.left_layout.addWidget(self.file_list)
        
        self.btn_recognize = QPushButton("识别当前文件夹全部音频 (Recognize All)")
        self.btn_recognize.setToolTip("识别当前文件夹下的所有音频文件")
        self.btn_recognize.clicked.connect(self.transcribe_directory)
        self.left_layout.addWidget(self.btn_recognize)

        self.splitter.addWidget(self.left_panel)

        # Right Panel
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.right_splitter = QSplitter(Qt.Vertical)
        self.right_layout.addWidget(self.right_splitter)

        # Target 1
        self.target_widget_1 = QWidget()
        self.target_layout_1 = QVBoxLayout(self.target_widget_1)
        self.target_layout_1.setContentsMargins(0, 0, 0, 0)
        
        self.header_widget_1 = QWidget()
        self.header_layout_1 = QHBoxLayout(self.header_widget_1)
        self.header_layout_1.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_target_1 = QLabel("文件夹 A (Folder A)")
        self.lbl_target_1.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.btn_toggle_target_2 = QPushButton("+ 显示文件夹 B")
        self.btn_toggle_target_2.setCheckable(True)
        self.btn_toggle_target_2.clicked.connect(self.toggle_target_2)
        
        self.btn_select_target_1 = QPushButton("选择文件夹")
        self.btn_select_target_1.clicked.connect(self.select_target_directory_1)
        
        self.header_layout_1.addWidget(self.lbl_target_1)
        self.header_layout_1.addStretch()
        self.header_layout_1.addWidget(self.btn_toggle_target_2)
        self.header_layout_1.addWidget(self.btn_select_target_1)
        self.target_layout_1.addWidget(self.header_widget_1)
        
        self.column_view_1 = DraggableColumnView()
        self.column_view_1.setStyleSheet("QColumnView::item { padding: 5px; height: 30px; }")
        self.target_model_1 = QFileSystemModel()
        self.target_model_1.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        self.target_model_1.setNameFilters(["*.wav", "*.mp3", "*.flac", "*.m4a"])
        self.target_model_1.setNameFilterDisables(False)
        self.target_model_1.setReadOnly(False)
        self.column_view_1.setModel(self.target_model_1)
        self.column_view_1.setContextMenuPolicy(Qt.CustomContextMenu)
        self.column_view_1.customContextMenuRequested.connect(lambda pos: self.show_target_context_menu(pos, self.column_view_1, self.target_model_1))
        self.target_layout_1.addWidget(self.column_view_1)
        self.right_splitter.addWidget(self.target_widget_1)

        # Target 2
        self.target_widget_2 = QWidget()
        self.target_layout_2 = QVBoxLayout(self.target_widget_2)
        self.target_layout_2.setContentsMargins(0, 0, 0, 0)
        
        self.header_widget_2 = QWidget()
        self.header_layout_2 = QHBoxLayout(self.header_widget_2)
        self.header_layout_2.setContentsMargins(5, 5, 5, 5)
        
        self.lbl_target_2 = QLabel("文件夹 B (Folder B)")
        self.lbl_target_2.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.btn_close_target_2 = QPushButton("×")
        self.btn_close_target_2.setFixedSize(24, 24)
        self.btn_close_target_2.clicked.connect(self.hide_target_2)
        
        self.btn_select_target_2 = QPushButton("选择文件夹")
        self.btn_select_target_2.clicked.connect(self.select_target_directory_2)
        
        self.header_layout_2.addWidget(self.lbl_target_2)
        self.header_layout_2.addStretch()
        self.header_layout_2.addWidget(self.btn_select_target_2)
        self.header_layout_2.addWidget(self.btn_close_target_2)
        self.target_layout_2.addWidget(self.header_widget_2)
        
        self.column_view_2 = DraggableColumnView()
        self.column_view_2.setStyleSheet("QColumnView::item { padding: 5px; height: 30px; }")
        self.target_model_2 = QFileSystemModel()
        self.target_model_2.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        self.target_model_2.setNameFilters(["*.wav", "*.mp3", "*.flac", "*.m4a"])
        self.target_model_2.setNameFilterDisables(False)
        self.target_model_2.setReadOnly(False)
        self.column_view_2.setModel(self.target_model_2)
        self.column_view_2.setContextMenuPolicy(Qt.CustomContextMenu)
        self.column_view_2.customContextMenuRequested.connect(lambda pos: self.show_target_context_menu(pos, self.column_view_2, self.target_model_2))
        self.target_layout_2.addWidget(self.column_view_2)
        self.right_splitter.addWidget(self.target_widget_2)
        
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([400, 600])
        self.right_splitter.setSizes([450, 450])

        self.target_path_1 = ""
        self.target_path_2 = ""
        self.clipboard_files = []
        self.is_cut_operation = False
        self.undo_stack = []
        
        self.undo_shortcut = QShortcut(QKeySequence.Undo, self)
        self.undo_shortcut.activated.connect(self.undo_last_operation)
        
        self.settings = QSettings("PomodoroWidget", "VoiceOrganizer")
        self.load_settings()

    def record_undo(self, moved_files):
        self.undo_stack.append(moved_files)
        print(f"Recorded undo step with {len(moved_files)} files")

    def undo_last_operation(self):
        if not self.undo_stack:
            QMessageBox.information(self, "撤销", "没有可撤销的操作")
            return

        last_moves = self.undo_stack.pop()
        restored_count = 0
        for original_src, current_dst in reversed(last_moves):
            if os.path.exists(current_dst):
                try:
                    os.makedirs(os.path.dirname(original_src), exist_ok=True)
                    shutil.move(current_dst, original_src)
                    restored_count += 1
                    print(f"Undoing: {current_dst} -> {original_src}")
                except Exception as e:
                    print(f"Failed to undo {current_dst}: {e}")
        
        if restored_count > 0:
            print(f"Undo complete: {restored_count} files restored")
        else:
            QMessageBox.warning(self, "撤销失败", "无法找到之前移动的文件")

    def toggle_target_2(self):
        visible = self.btn_toggle_target_2.isChecked()
        self.target_widget_2.setVisible(visible)
        self.btn_toggle_target_2.setText("- 隐藏文件夹 B" if visible else "+ 显示文件夹 B")

    def hide_target_2(self):
        self.target_widget_2.setVisible(False)
        self.btn_toggle_target_2.setChecked(False)
        self.btn_toggle_target_2.setText("+ 显示文件夹 B")

    def load_settings(self):
        geo = self.settings.value("geometry")
        if geo: self.restoreGeometry(geo)
            
        src = self.settings.value("source_path")
        if src and os.path.exists(src):
            self.lbl_src_path.setText(src)
            self.file_list.setRootIndex(self.file_model.setRootPath(src))
            
        t1 = self.settings.value("target_path_1")
        if not t1 or not os.path.exists(t1):
             t1 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds")
             if not os.path.exists(t1): t1 = QDir.currentPath()
        self.target_path_1 = t1
        self.target_model_1.setRootPath(t1)
        self.column_view_1.setRootIndex(self.target_model_1.index(t1))
        self.lbl_target_1.setText(f"文件夹 A: {os.path.basename(t1)}")
        
        t2 = self.settings.value("target_path_2")
        if not t2 or not os.path.exists(t2): t2 = t1
        self.target_path_2 = t2
        self.target_model_2.setRootPath(t2)
        self.column_view_2.setRootIndex(self.target_model_2.index(t2))
        self.lbl_target_2.setText(f"文件夹 B: {os.path.basename(t2)}")
        
        show_t2 = self.settings.value("show_target_2", False, type=bool)
        self.target_widget_2.setVisible(show_t2)
        self.btn_toggle_target_2.setChecked(show_t2)
        self.btn_toggle_target_2.setText("- 隐藏文件夹 B" if show_t2 else "+ 显示文件夹 B")

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("show_target_2", self.target_widget_2.isVisible())
        super().closeEvent(event)

    def select_source_directory(self):
        d = QFileDialog.getExistingDirectory(self, "选择包含录音的文件夹")
        if d:
            self.lbl_src_path.setText(d)
            self.file_list.setRootIndex(self.file_model.setRootPath(d))
            self.settings.setValue("source_path", d)

    def select_target_directory_1(self):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹 A")
        if d:
            self.target_path_1 = d
            self.target_model_1.setRootPath(d)
            self.column_view_1.setRootIndex(self.target_model_1.index(d))
            self.lbl_target_1.setText(f"文件夹 A: {os.path.basename(d)}")
            self.settings.setValue("target_path_1", d)

    def select_target_directory_2(self):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹 B")
        if d:
            self.target_path_2 = d
            self.target_model_2.setRootPath(d)
            self.column_view_2.setRootIndex(self.target_model_2.index(d))
            self.lbl_target_2.setText(f"文件夹 B: {os.path.basename(d)}")
            self.settings.setValue("target_path_2", d)

    def show_context_menu(self, position):
        indexes = self.file_list.selectedIndexes()
        paths = [self.file_model.filePath(i) for i in indexes if i.column() == 0]
        if not paths: return
        
        menu = QMenu()
        
        # Play action in context menu
        if len(paths) == 1 and os.path.isfile(paths[0]):
            play_action = menu.addAction("播放 (Play)")
            play_action.triggered.connect(self.play_selected_file)
            menu.addSeparator()

        # Transcribe action
        if any(os.path.isfile(p) for p in paths):
            transcribe_action = menu.addAction("识别 (Recognize)")
            transcribe_action.triggered.connect(self.transcribe_selected_files)
            menu.addSeparator()

        menu.addAction("剪切 (Cut)", lambda: self.copy_to_clipboard(paths, True))
        menu.addAction("复制 (Copy)", lambda: self.copy_to_clipboard(paths, False))
        menu.addSeparator()
        
        if self.target_path_1 and os.path.exists(self.target_path_1):
             idx1 = self.column_view_1.selectionModel().currentIndex()
             t1 = self.target_model_1.filePath(idx1) if idx1.isValid() else self.target_path_1
             if os.path.isfile(t1): t1 = os.path.dirname(t1)
             menu.addAction(f"移动至文件夹 A: {os.path.basename(t1)}", lambda: self.move_files_to(paths, t1))

        if self.target_path_2 and os.path.exists(self.target_path_2):
             idx2 = self.column_view_2.selectionModel().currentIndex()
             t2 = self.target_model_2.filePath(idx2) if idx2.isValid() else self.target_path_2
             if os.path.isfile(t2): t2 = os.path.dirname(t2)
             menu.addAction(f"移动至文件夹 B: {os.path.basename(t2)}", lambda: self.move_files_to(paths, t2))

        if self.clipboard_files:
            menu.addSeparator()
            idx = indexes[0] if indexes else self.file_list.rootIndex()
            t_dir = self.file_model.filePath(idx)
            if os.path.isfile(t_dir): t_dir = os.path.dirname(t_dir)
            if not t_dir: t_dir = self.file_model.rootPath()
            menu.addAction(f"粘贴 {len(self.clipboard_files)} 个文件", lambda: self.paste_files(t_dir))
        
        menu.exec(self.file_list.viewport().mapToGlobal(position))

    def show_target_context_menu(self, position, view, model):
        index = view.indexAt(position)
        menu = QMenu()
        
        if index.isValid():
            paths = list(set([model.filePath(i) for i in view.selectionModel().selectedIndexes()]))
            if not paths: paths = [model.filePath(index)]
            menu.addAction("剪切 (Cut)", lambda: self.copy_to_clipboard(paths, True))
            menu.addAction("复制 (Copy)", lambda: self.copy_to_clipboard(paths, False))

        if self.clipboard_files:
            if not menu.isEmpty(): menu.addSeparator()
            t_dir = model.filePath(index) if index.isValid() else model.rootPath()
            if os.path.isfile(t_dir): t_dir = os.path.dirname(t_dir)
            if not t_dir and view.rootIndex().isValid(): t_dir = model.filePath(view.rootIndex())
            menu.addAction(f"粘贴 {len(self.clipboard_files)} 个文件", lambda: self.paste_files(t_dir))
            
        menu.exec(view.viewport().mapToGlobal(position))

    def paste_files(self, target_dir):
        if not self.clipboard_files or not os.path.exists(target_dir): return
        files_moved = []
        for src in self.clipboard_files:
            if not os.path.exists(src): continue
            dst = os.path.join(target_dir, os.path.basename(src))
            if os.path.abspath(src) == os.path.abspath(dst): continue
            try:
                if self.is_cut_operation:
                    shutil.move(src, dst)
                    files_moved.append((src, dst))
                    print(f"Pasted (Cut): {src} -> {dst}")
                else:
                    if os.path.isdir(src): shutil.copytree(src, dst)
                    else: shutil.copy2(src, dst)
                    print(f"Pasted (Copy): {src} -> {dst}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"处理失败: {e}")

        if self.is_cut_operation:
            if files_moved: self.record_undo(files_moved)
            self.clipboard_files = []
            self.is_cut_operation = False

    def copy_to_clipboard(self, paths, is_cut):
        self.clipboard_files = paths
        self.is_cut_operation = is_cut
        print(f"已{'剪切' if is_cut else '复制'} {len(paths)} 个文件")

    def move_files_to(self, paths, target_dir):
        files_moved = []
        for src in paths:
            if not os.path.exists(src): continue
            dst = os.path.join(target_dir, os.path.basename(src))
            try:
                shutil.move(src, dst)
                files_moved.append((src, dst))
                print(f"Moved: {src} -> {dst}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"移动失败: {e}")
        if files_moved: self.record_undo(files_moved)

    def transcribe_directory(self):
        self.stop_audio() # Stop playback to release file locks
        root_path = self.file_model.rootPath()
        if not root_path or not os.path.exists(root_path):
             QMessageBox.information(self, "提示", "请先选择源文件夹")
             return

        # Find all audio files in the directory
        valid_files = []
        valid_exts = [".wav", ".mp3", ".flac", ".m4a"]
        
        try:
            for file_name in os.listdir(root_path):
                full_path = os.path.join(root_path, file_name)
                if os.path.isfile(full_path):
                    ext = os.path.splitext(full_path)[1].lower()
                    if ext in valid_exts:
                        valid_files.append(full_path)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取文件夹: {e}")
            return

        if not valid_files:
            QMessageBox.information(self, "提示", "当前文件夹没有可识别的音频文件")
            return
            
        # Confirmation
        reply = QMessageBox.question(self, "批量识别", 
                                     f"即将识别当前文件夹下的 {len(valid_files)} 个音频文件。\n这可能需要一些时间，是否继续？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.No:
            return

        self.statusBar().showMessage(f"开始批量识别 {len(valid_files)} 个文件...", 3000)
        
        # Get selected language
        lang_text = self.combo_language.currentText()
        language = "auto"
        if "中文" in lang_text: language = "zh"
        elif "日语" in lang_text: language = "ja"
        elif "英语" in lang_text: language = "en"

        for file_path in valid_files:
            self.file_model.update_transcription(file_path, "⏳ 正在识别... (Recognizing...)")
            self.transcriber.start_transcription(file_path, partial=True, language=language)

    def transcribe_selected_files(self):
        self.stop_audio() # Stop playback to release file locks
        indexes = self.file_list.selectedIndexes()
        paths = set([self.file_model.filePath(i) for i in indexes if i.column() == 0])
        
        valid_files = [p for p in paths if os.path.isfile(p)]
        
        if not valid_files:
            QMessageBox.information(self, "提示", "请先选择要识别的音频文件")
            return

        self.statusBar().showMessage(f"开始识别 {len(valid_files)} 个文件...", 3000)
        
        # Get selected language
        lang_text = self.combo_language.currentText()
        language = "auto"
        if "中文" in lang_text: language = "zh"
        elif "日语" in lang_text: language = "ja"
        elif "英语" in lang_text: language = "en"

        for file_path in valid_files:
            self.file_model.update_transcription(file_path, "⏳ 正在识别... (Recognizing...)")
            self.transcriber.start_transcription(file_path, partial=True, language=language)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self.undo_last_operation()
        super().keyPressEvent(event)

    def play_selected_file(self):
        index = self.file_list.currentIndex()
        if not index.isValid(): return
        
        file_path = self.file_model.filePath(index)
        if not os.path.isfile(file_path): return
        
        self.audio_controller.play(file_path)
        
        self.lbl_now_playing.setText(f"Playing: {os.path.basename(file_path)}")
        self.action_play.setEnabled(False)
        self.action_stop.setEnabled(True)

    def stop_audio(self):
        self.audio_controller.stop()
        self.lbl_now_playing.setText("Stopped")
        self.action_play.setEnabled(True)
        self.action_stop.setEnabled(False)

    def handle_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.stop_audio()
            self.lbl_now_playing.setText("Finished")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoiceOrganizer()
    window.show()
    sys.exit(app.exec())
