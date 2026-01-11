import os
import shutil
import random
from PySide6.QtWidgets import (QApplication, QFileSystemModel, QStyledItemDelegate, QStyle, 
                               QTreeView, QColumnView, QAbstractItemView, QMessageBox)
from PySide6.QtCore import Qt, QModelIndex, QDir, QRect, QObject, QUrl
from PySide6.QtGui import QAction, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

# Mock Data for Transcription
MOCK_TEXTS = [
    "请点击“识别”按钮获取真实文本...",
]

class AudioController(QObject):
    """Controller for audio playback."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

    def play(self, file_path):
        self.stop()
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.player.play()

    def stop(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.stop()

class MockTranscriptionFileSystemModel(QFileSystemModel):
    def __init__(self):
        super().__init__()
        self.mock_cache = {}

    def update_transcription(self, file_path, text):
        """Updates the cache with real transcription and notifies the view."""
        norm_path = os.path.normpath(file_path)
        self.mock_cache[norm_path] = text
        
        # Notify view about the change
        index = self.index(file_path)
        if index.isValid():
             self.dataChanged.emit(index, index, [Qt.DisplayRole])
        else:
             # Try forcing a refresh of the parent directory if index is invalid
             # This happens if the model hasn't fully loaded the file yet
             pass

    def columnCount(self, parent=QModelIndex()):
        return super().columnCount(parent) + 1

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == super().columnCount() - 1: # Last column
                return "识别文本"
        return super().headerData(section, orientation, role)

    def data(self, index, role):
        if index.column() == self.columnCount() - 1:
            if role == Qt.DisplayRole:
                name_index = index.siblingAtColumn(0)
                file_path = self.filePath(name_index)
                if os.path.isfile(file_path):
                    norm_path = os.path.normpath(file_path)
                    if norm_path not in self.mock_cache:
                        # Default placeholder
                        return "" 
                    return self.mock_cache[norm_path]
                return ""
        return super().data(index, role)

class SubtitleDelegate(QStyledItemDelegate):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.fs_model = model

    def paint(self, painter, option, index):
        if index.column() == 0:
            painter.save()
            self.initStyleOption(option, index)
            style = option.widget.style() if option.widget else QApplication.style()
            style.drawPrimitive(QStyle.PE_PanelItemViewItem, option, painter, option.widget)
            
            file_name = index.data(Qt.DisplayRole)
            file_path = self.fs_model.filePath(index)
            norm_path = os.path.normpath(file_path)
            
            # Draw file name
            text_rect = option.rect
            text_x = text_rect.x() + 5
            text_y = text_rect.y() + 5
            
            # Icon
            icon = self.fs_model.fileIcon(index)
            icon.paint(painter, text_x, text_y, 16, 16)
            text_x += 20
            
            painter.setPen(Qt.black)
            painter.drawText(text_x, text_y + 12, file_name)
            
            # Draw Subtitle if exists
            mock_text = ""
            if os.path.isfile(file_path):
                if hasattr(self.fs_model, 'mock_cache'):
                    mock_text = self.fs_model.mock_cache.get(norm_path, "")
            
            if mock_text:
                text_width = text_rect.width() - 30
                subtitle_rect = QRect(text_x, text_y + 20, text_width, 48) # Allow ~3 lines
                
                # Check for error message
                if mock_text.startswith("【错误】"):
                    painter.setPen(QColor("red"))
                else:
                    painter.setPen(QColor("gray"))
                
                # Word wrap
                flags = Qt.TextWordWrap | Qt.AlignTop | Qt.AlignLeft
                
                # Truncate text if too long (simple char limit for safety + ellipsis handled by drawText if rect too small? No, drawText clips.)
                # But we want ellipsis at the end of the 3rd line.
                # Qt.ElideRight works for single line. For multi-line, it's harder.
                # We limit characters to ~100.
                MAX_CHARS = 100
                display_text = mock_text
                if len(display_text) > MAX_CHARS:
                    display_text = display_text[:MAX_CHARS] + "..."
                
                painter.drawText(subtitle_rect, flags, display_text)

            painter.restore()
        else:
            super().paint(painter, option, index)

    def sizeHint(self, option, index):
        if index.column() == 0:
            return QSize(200, 80) # Fixed height for now
        return super().sizeHint(option, index)

class DraggableTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            index = self.indexAt(event.position().toPoint())
            model = self.model()
            target_path = model.rootPath()
            if index.isValid():
                target_path = model.filePath(index)
                if os.path.isfile(target_path):
                    target_path = os.path.dirname(target_path)
            
            if not os.path.isdir(target_path):
                target_path = model.rootPath()

            files_moved = []
            for url in event.mimeData().urls():
                src_path = url.toLocalFile()
                if not os.path.exists(src_path): continue
                file_name = os.path.basename(src_path)
                dst_path = os.path.join(target_path, file_name)
                if os.path.dirname(src_path) == target_path: continue

                try:
                    shutil.move(src_path, dst_path)
                    files_moved.append((src_path, dst_path))
                    print(f"Dropped & Moved: {src_path} -> {dst_path}")
                except Exception as e:
                    print(f"Error moving {file_name}: {e}")
            
            if files_moved:
                event.acceptProposedAction()
                main_window = self.window()
                if hasattr(main_window, 'record_undo'):
                    main_window.record_undo(files_moved)
        else:
            super().dropEvent(event)

class DraggableColumnView(QColumnView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)

    def createColumn(self, index):
        view = super().createColumn(index)
        view.setAcceptDrops(True)
        view.setDragDropMode(QAbstractItemView.DragDrop)
        view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        return view

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            index = self.indexAt(event.position().toPoint())
            model = self.model()
            target_path = model.filePath(index) if index.isValid() else model.rootPath()
            if os.path.isfile(target_path):
                target_path = os.path.dirname(target_path)
            
            if not os.path.isdir(target_path):
                target_path = model.rootPath()

            files_moved = []
            for url in event.mimeData().urls():
                src_path = url.toLocalFile()
                if os.path.exists(src_path):
                    file_name = os.path.basename(src_path)
                    dst_path = os.path.join(target_path, file_name)
                    if os.path.dirname(src_path) == target_path: continue

                    try:
                        shutil.move(src_path, dst_path)
                        files_moved.append((src_path, dst_path))
                        print(f"Dropped & Moved: {src_path} -> {dst_path}")
                    except Exception as e:
                        print(f"Error moving {file_name}: {e}")
            
            if files_moved:
                event.acceptProposedAction()
                main_window = self.window()
                if hasattr(main_window, 'record_undo'):
                    main_window.record_undo(files_moved)
        else:
            super().dropEvent(event)
