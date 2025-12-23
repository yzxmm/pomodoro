import os
import sys
import time
import urllib.request
import json
import threading
import random
from PySide6 import QtCore, QtGui, QtWidgets
from image_menu import ImageMenu
from download_manager import DownloadManager
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

# Set this to False to disable layout editing features (drag/resize time label)
LAYOUT_EDIT_MODE = True


import winsound

def base_dir():
    return os.path.dirname(os.path.abspath(__file__))


def asset_path(*parts):
    return os.path.join(base_dir(), "assets", *parts)


def sound_path(*parts):
    return os.path.join(base_dir(), "sounds", *parts)


def resolve_asset(name):
    local = asset_path(name)
    if os.path.exists(local):
        return local
    parent = os.path.join(os.path.dirname(base_dir()), "assets", name)
    return parent if os.path.exists(parent) else local


class PomodoroWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)

        self.image_label = QtWidgets.QLabel(self)
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setScaledContents(False)

        pix = QtGui.QPixmap(resolve_asset("idle.png"))
        if not pix.isNull():
            self.image_label.setPixmap(pix)
            self.resize(pix.size())
        else:
            self.resize(400, 400)

        self.image_label.setGeometry(0, 0, self.width(), self.height())

        self.time_label = QtWidgets.QLabel(self)
        self.time_label.setText("00:00")
        self.time_label.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(22)
        font.setBold(True)
        self.time_label.setFont(font)
        self.time_label.setStyleSheet("color: black;")
        
        # Layout config
        self.layout_config = {
            "time_x": 0.3,  # center
            "time_y": 0.61,
            "time_w": 0.39,
            "time_h": 0.11,
            "font_size": 22
        }
        
        self.place_time_label()

        self.work_duration = 40 * 60
        self.rest_duration = 15 * 60
        self.elapsed = 0
        self.phase = "idle"
        self.paused = False
        self.always_on_top = True
        self.adjusting_duration = False
        self.adjust_mode = None  # 'work' or 'rest'
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.duration_start = self.work_duration
        self.exit_on_work_end = False

        self.tick_timer = QtCore.QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self.on_tick)

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.sound_queue = []
        self.pool_start = []
        self.pool_end = []
        self.pool_ten = []
        self.pool_resume = []
        self.random_pool = []  # 通用兜底池
        self.seasonal_pools = {'start': {}, 'end': {}, 'ten': {}, 'resume': {}}
        self.tag_pools = {'start': {}, 'end': {}, 'ten': {}, 'resume': {}}
        self.ten_voice_enabled = self.env_flag_enabled('POMODORO_TEN_ENABLE', default=True)
        self.voice_interval_minutes = 10
        self.build_sound_pool()
        self.update_sounds_async()

        self.load_settings()

        self.time_label.installEventFilter(self)

        self.dragging = False
        self.drag_offset = QtCore.QPoint()
        # digit image container for hand-written PNG digits (optional)
        self.digit_container = QtWidgets.QWidget(self)
        # self.digit_container.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.digit_layout = QtWidgets.QHBoxLayout(self.digit_container)
        self.digit_layout.setContentsMargins(0, 0, 0, 0)
        self.digit_layout.setSpacing(0)
        self.digit_labels = [QtWidgets.QLabel(self.digit_container) for _ in range(5)]
        for lbl in self.digit_labels:
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setScaledContents(False)
            self.digit_layout.addWidget(lbl)
        self.digit_container.hide()
        
        # Install event filter on digit_container and its children to allow dragging
        self.digit_container.installEventFilter(self)
        for lbl in self.digit_labels:
            lbl.installEventFilter(self)

        # 确保初始几何同步
        self.place_time_label()

        self.set_time_text(self.format_time(self.work_duration))
        self.menu_overlay = ImageMenu(self)

        self.resume_button = QtWidgets.QLabel(self)
        self.resume_button.setFixedSize(100, 100)
        self.resume_button.setAlignment(QtCore.Qt.AlignCenter)
        self.resume_button.setScaledContents(True)
        rpix = QtGui.QPixmap(resolve_asset("resume.png"))
        if not rpix.isNull():
            self.resume_button.setPixmap(rpix)
        else:
            self.resume_button.setText("继续")
            self.resume_button.setStyleSheet("background: rgba(0,0,0,0.3); color: white; padding:6px; border-radius:6px;")
        self.resume_button.hide()
        self.resume_button.mousePressEvent = lambda e: (self.start_or_resume(), e.accept())
        self.resume_offset_y_ratio = 0.08

        self.start_button = QtWidgets.QPushButton("开始", self)
        s_icon = resolve_asset("start_btn.png")
        if os.path.exists(s_icon):
            self.start_button.setText("")
            self.start_button.setIcon(QtGui.QIcon(s_icon))
            self.start_button.setIconSize(QtCore.QSize(40, 40))
            self.start_button.setFixedSize(50, 50)
            self.start_button.setStyleSheet("border: none; background: transparent;")
        else:
            self.start_button.setFixedSize(88, 34)
        self.start_button.clicked.connect(self.start_or_resume)
        self.start_button.show()
        self.place_start_button()

    def place_time_label(self):
        w = self.width()
        h = self.height()
        
        # Use config if available, fallback to defaults
        cfg = getattr(self, 'layout_config', {})
        rel_x = cfg.get("time_x", 0.3)
        rel_y = cfg.get("time_y", 0.61)
        rel_w = cfg.get("time_w", 0.39)
        rel_h = cfg.get("time_h", 0.11)
        
        # Validate coordinates (prevent out of screen)
        if rel_x < 0 or rel_x > 1 or rel_y < 0 or rel_y > 1:
            rel_x = 0.3
            rel_y = 0.61
            rel_w = 0.39
            rel_h = 0.11
            # Update config with safe values
            self.layout_config['time_x'] = rel_x
            self.layout_config['time_y'] = rel_y
            self.layout_config['time_w'] = rel_w
            self.layout_config['time_h'] = rel_h
        
        x = int(w * rel_x)
        y = int(h * rel_y)
        label_w = int(w * rel_w)
        label_h = int(h * rel_h)
        
        self.time_label.setGeometry(x, y, label_w, label_h)
        
        # Update font size if needed
        f_size = cfg.get("font_size", 22)
        font = self.time_label.font()
        if font.pointSize() != f_size:
            font.setPointSize(f_size)
            self.time_label.setFont(font)
        
        # Auto-expand label width/height if text might clip, but respect layout config if it was manually set?
        # Actually, let's just make sure the label is large enough to contain the text
        if LAYOUT_EDIT_MODE:
            self.time_label.adjustSize()
            # Update w/h in config to match the new size relative to window
            # But wait, adjustSize() might make it smaller if text is short (e.g. 00:00)
            # We want to keep the box reasonably sized.
            # Let's just update the geometry to be at least the calculated size, or use adjustSize logic
            
            # If we just resized font, the adjustSize will calculate needed rect
            curr_geo = self.time_label.geometry()
            # Update stored relative width/height so it persists
            self.layout_config['time_w'] = curr_geo.width() / w
            self.layout_config['time_h'] = curr_geo.height() / h
        else:
            # If edit mode is disabled, we must ensure the label is visible and large enough
            # We trust the stored relative coordinates, but maybe force adjustSize for content?
            # If we don't adjustSize, and font is large, it might clip.
            # So let's force adjustSize to ensure visibility, then center it at the configured position?
            # Or just rely on the stored geometry.
            # If the user messed up the geometry in edit mode (e.g. made it 0x0), it would be hidden.
            # Safety check:
            if label_w < 10 or label_h < 10:
                self.time_label.adjustSize()
                new_geo = self.time_label.geometry()
                self.time_label.setGeometry(x, y, new_geo.width(), new_geo.height())
            
        if hasattr(self, 'digit_container') and self.digit_container is not None:
            self.digit_container.setGeometry(self.time_label.geometry())
            # Re-render digits if they are active to match new size
            if self.digits_available() and self.time_label.text():
                self.show_digit_time(self.time_label.text())

    def place_resume_button(self):
        w = self.width()
        h = self.height()
        bw = self.resume_button.width()
        bh = self.resume_button.height()
        rx = int((w - bw) / 2)
        ry = max(0, int((h - bh) / 2 - h * self.resume_offset_y_ratio))
        self.resume_button.setGeometry(rx, ry, bw, bh)

    def place_start_button(self):
        w = self.width()
        h = self.height()
        bw = self.start_button.width()
        bh = self.start_button.height()
        margin = max(6, int(min(w, h) * 0.015))
        rx = max(0, w - bw - margin)
        ry = margin
        self.start_button.setGeometry(rx, ry, bw, bh)

    def resizeEvent(self, event):
        self.image_label.setGeometry(0, 0, self.width(), self.height())
        # Ensure time label is placed correctly on resize
        self.place_time_label()
        self.place_resume_button()
        self.place_start_button()
        super().resizeEvent(event)

    def wheelEvent(self, event):
        if LAYOUT_EDIT_MODE and (event.modifiers() & QtCore.Qt.ControlModifier):
            delta = event.angleDelta().y()
            current_size = self.layout_config.get('font_size', 22)
            if delta > 0:
                new_size = min(120, current_size + 2)
            else:
                new_size = max(8, current_size - 2)
            
            if new_size != current_size:
                self.layout_config['font_size'] = new_size
                self.place_time_label()
                self.save_settings()
            event.accept()
        else:
            super().wheelEvent(event)

    def format_time(self, seconds):
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def digits_available(self):
        local_dir = os.path.join(base_dir(), "assets", "digits")
        parent_dir = os.path.join(os.path.dirname(base_dir()), "assets", "digits")
        check_dir = local_dir if os.path.exists(local_dir) else parent_dir
        return os.path.exists(os.path.join(check_dir, "0.png")) and os.path.exists(os.path.join(check_dir, "colon.png"))

    def digit_path(self, ch):
        name = "colon.png" if ch == ":" else f"{ch}.png"
        local = os.path.join(base_dir(), "assets", "digits", name)
        if os.path.exists(local):
            return local
        parent = os.path.join(os.path.dirname(base_dir()), "assets", "digits", name)
        return parent if os.path.exists(parent) else local

    def set_time_text(self, text):
        if self.digits_available():
            # Keep text for size calculation but hide label
            self.time_label.setText(text)
            self.time_label.hide()
            self.show_digit_time(text)
        else:
            self.digit_container.hide()
            self.time_label.show()
            self.time_label.setText(text)
            self.time_label.adjustSize()

    def show_digit_time(self, text):
        chars = [text[0], text[1], ":", text[3], text[4]]
        pixmaps = []
        for ch in chars:
            p = self.digit_path(ch)
            pm = QtGui.QPixmap(p)
            pixmaps.append(pm if not pm.isNull() else QtGui.QPixmap())
        
        # Calculate optimal height to fit both width and height of the container
        container_w = max(1, self.digit_container.width())
        container_h = max(1, self.digit_container.height())
        
        # 1. Try scaling to full height first
        temp_height = container_h
        total_w_at_full_height = 0
        for pm in pixmaps:
            if not pm.isNull():
                # w = pm.width() * (temp_height / pm.height())
                total_w_at_full_height += pm.width() * (temp_height / max(1, pm.height()))
            else:
                total_w_at_full_height += temp_height * 0.5 # assume aspect ratio 0.5 for missing
        
        # Add padding estimate (approx 6% of height per digit)
        # Fix truncation: increase padding slightly or ensure container is wide enough
        # The container width is fixed by geometry. If digits + padding > container width, we scale down.
        # But if padding calculation is too aggressive, it might overflow visually?
        # Actually, let's just make sure we use available width efficiently.
        
        # Reduce internal padding calculation to tighten spacing
        pad_px = temp_height * -0.04
        total_w_at_full_height += pad_px * 5
        
        # 2. If too wide, scale down height
        # Ensure we have a tiny bit of margin so it doesn't touch edges exactly
        safe_container_w = container_w * 0.95 # Increase safety margin to 5% to prevent right side cut
        
        if total_w_at_full_height > safe_container_w:
            scale_factor = safe_container_w / total_w_at_full_height
            final_height = int(temp_height * scale_factor)
        else:
            final_height = temp_height
            
        final_height = max(1, final_height)
        
        scaled = []
        for pm in pixmaps:
            if pm.isNull():
                scaled.append(QtGui.QPixmap())
            else:
                scaled.append(pm.scaledToHeight(final_height, QtCore.Qt.SmoothTransformation))
                
        for i, spm in enumerate(scaled):
            self.digit_labels[i].setPixmap(spm)
            self.digit_labels[i].setFixedHeight(final_height)
            # Allow label to be its natural width
            if not spm.isNull():
                self.digit_labels[i].setFixedWidth(spm.width())
            else:
                self.digit_labels[i].setFixedWidth(max(1, int(final_height * 0.5)))
                
        # Tighten layout spacing
        self.digit_layout.setSpacing(int(final_height * -0.04))
        self.digit_layout.setContentsMargins(0, 0, 0, 0)
        
        self.digit_container.show()
        self.digit_container.raise_()

    def start_or_resume(self):
        if self.phase == "idle":
            self.phase = "working"
            self.elapsed = 0
            self.set_time_text(self.format_time(self.elapsed))
            self.tick_timer.start()
            self.play_category('start', default_file='start.mp3')
            self.apply_phase_visuals()
        elif self.paused:
            self.paused = False
            self.tick_timer.start()
            self.play_category('resume', default_file='resume.mp3')
            self.apply_phase_visuals()
        self.start_button.hide()

    def pause_timer(self):
        if self.tick_timer.isActive():
            self.tick_timer.stop()
            self.paused = True
            self.apply_phase_visuals()

    def on_tick(self):
        self.elapsed += 1
        self.set_time_text(self.format_time(self.elapsed))
        self.maybe_interval_voice()
        if self.phase == "working" and self.elapsed >= self.work_duration:
            self.play_category('end', default_file='end.mp3')
            if self.exit_on_work_end:
                QtWidgets.QApplication.quit()
                return
            self.phase = "rest"
            self.elapsed = 0
            self.play_sound("rest_start.mp3")
            self.apply_phase_visuals()
        elif self.phase == "rest" and self.elapsed >= self.rest_duration:
            self.phase = "working"
            self.elapsed = 0
            self.play_category('start', default_file='start.mp3')
            self.apply_phase_visuals()

    def apply_phase_visuals(self):
        if self.paused:
            pix = QtGui.QPixmap(resolve_asset("paused.png"))
        elif self.phase == "rest":
            pix = QtGui.QPixmap(resolve_asset("paused.png"))
        elif self.phase == "working":
            pix = QtGui.QPixmap(resolve_asset("idle.png"))
        else:
            pix = QtGui.QPixmap(resolve_asset("idle.png"))
        if not pix.isNull():
            self.image_label.setPixmap(pix)
            self.resize(pix.size())
        if self.paused:
            self.resume_button.show()
            self.place_resume_button()
        else:
            self.resume_button.hide()
        if self.phase == "idle" and not self.paused:
            self.start_button.show()
            self.place_start_button()
        else:
            self.start_button.hide()

    def play_sound(self, file_name_or_path):
        path = file_name_or_path
        if not os.path.isabs(path):
            local = sound_path(file_name_or_path)
            path = local if os.path.exists(local) else os.path.join(os.path.dirname(base_dir()), "sounds", file_name_or_path)
        if os.path.exists(path):
            url = QtCore.QUrl.fromLocalFile(path)
            self.sound_queue.append(url)
            if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self.start_next_sound()

    def on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.start_next_sound()

    def start_next_sound(self):
        if self.sound_queue:
            url = self.sound_queue.pop(0)
            self.player.setSource(url)
            self.player.play()

    def eventFilter(self, obj, event):
        # Allow dragging from digit container or its labels
        is_time_obj = (obj is self.time_label) or (obj is self.digit_container) or (obj in self.digit_labels)
        
        if is_time_obj and LAYOUT_EDIT_MODE:
            # Control + Left Click to move the label
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton and (event.modifiers() & QtCore.Qt.ControlModifier):
                self.label_dragging = True
                self.label_drag_start = event.globalPosition().toPoint()
                self.label_orig_pos = self.time_label.pos()
                return True
            
            if event.type() == QtCore.QEvent.MouseMove and getattr(self, 'label_dragging', False):
                delta = event.globalPosition().toPoint() - self.label_drag_start
                new_pos = self.label_orig_pos + delta
                
                # Update config
                w, h = self.width(), self.height()
                self.layout_config['time_x'] = new_pos.x() / w
                self.layout_config['time_y'] = new_pos.y() / h
                self.place_time_label()
                return True

            if event.type() == QtCore.QEvent.MouseButtonRelease and getattr(self, 'label_dragging', False):
                self.label_dragging = False
                self.save_settings()
                return True

        if is_time_obj:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                self.adjusting_duration = True
                self.adjust_mode = 'rest' if (event.modifiers() & QtCore.Qt.AltModifier) else 'work'
                self.drag_start_x = event.globalPosition().x() if hasattr(event, 'globalPosition') else event.globalX()
                self.drag_start_y = event.globalPosition().y() if hasattr(event, 'globalPosition') else event.globalY()
                self.duration_start = self.work_duration if self.adjust_mode == 'work' else self.rest_duration
                if self.adjust_mode == 'rest':
                    pix = QtGui.QPixmap(resolve_asset("paused.png"))
                    if not pix.isNull():
                        self.image_label.setPixmap(pix)
                        self.resize(pix.size())
                return True
            if event.type() == QtCore.QEvent.MouseMove and self.adjusting_duration and (event.buttons() & QtCore.Qt.LeftButton):
                x = event.globalPosition().x() if hasattr(event, 'globalPosition') else event.globalX()
                y = event.globalPosition().y() if hasattr(event, 'globalPosition') else event.globalY()
                dx = x - self.drag_start_x
                dy = self.drag_start_y - y
                ax = abs(dx)
                ay = abs(dy)
                deadzone_sec = 20
                deadzone_min = 10
                eff_ax = max(0, ax - deadzone_sec)
                eff_ay = max(0, ay - deadzone_min)
                if eff_ax < eff_ay * 0.75:
                    sec_delta = 0
                else:
                    sec_delta = int((eff_ax / 40) ** 1.2) * (1 if dx > 0 else -1)
                min_delta = int((eff_ay / 60) ** 1.1) * (1 if dy > 0 else -1)
                new_dur = int(self.duration_start + min_delta * 60 + sec_delta)
                if self.adjust_mode == 'work':
                    new_dur = max(300, min(3600, new_dur))
                    if new_dur != self.work_duration:
                        self.work_duration = new_dur
                        if self.phase == "idle" or self.paused:
                            self.set_time_text(self.format_time(self.work_duration))
                else:
                    new_dur = max(30, min(900, new_dur))
                    if new_dur != self.rest_duration:
                        self.rest_duration = new_dur
                        if self.phase == "idle" or self.paused:
                            self.set_time_text(self.format_time(self.rest_duration))
                if self.adjust_mode == 'rest':
                    pix = QtGui.QPixmap(resolve_asset("paused.png"))
                    if not pix.isNull():
                        self.image_label.setPixmap(pix)
                        self.resize(pix.size())
                return True
            if event.type() == QtCore.QEvent.MouseButtonRelease and self.adjusting_duration:
                self.adjusting_duration = False
                if self.phase == "idle":
                    target = self.work_duration if (self.adjust_mode == 'work') else self.rest_duration
                    self.set_time_text(self.format_time(target))
                    self.save_settings()
                else:
                    self.set_time_text(self.format_time(self.elapsed))
                self.adjust_mode = None
                self.apply_phase_visuals()
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def load_settings(self):
        settings_path = os.path.join(base_dir(), "settings.json")
        if not os.path.exists(settings_path):
            return
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.work_duration = data.get("work_duration", self.work_duration)
                self.rest_duration = data.get("rest_duration", self.rest_duration)
                self.always_on_top = data.get("always_on_top", self.always_on_top)
                self.voice_interval_minutes = data.get("voice_interval_minutes", self.voice_interval_minutes)
                self.exit_on_work_end = data.get("exit_on_work_end", self.exit_on_work_end)
                self.exit_voice_enabled = data.get("exit_voice_enabled", True)
                self.sounds_update_url = data.get("sounds_update_url", "")
                self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, self.always_on_top)
                
                # Restore layout config
                layout_cfg = data.get("layout_config")
                if layout_cfg:
                    self.layout_config.update(layout_cfg)
                    self.place_time_label()

                # Restore window position
                x = data.get("x")
                y = data.get("y")
                if x is not None and y is not None:
                    self.move(x, y)
                    
        except Exception as e:
            print(f"Failed to load settings: {e}")

    def save_settings(self):
        settings_path = os.path.join(base_dir(), "settings.json")
        data = {
            "work_duration": self.work_duration,
            "rest_duration": self.rest_duration,
            "always_on_top": self.always_on_top,
            "voice_interval_minutes": self.voice_interval_minutes,
            "exit_on_work_end": self.exit_on_work_end,
            "exit_voice_enabled": getattr(self, "exit_voice_enabled", True),
            "sounds_update_url": getattr(self, "sounds_update_url", ""),
            "layout_config": self.layout_config,
            "x": self.x(),
            "y": self.y()
        }
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if not self.adjusting_duration:
                self.dragging = True
                self.drag_offset = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.drag_offset)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False
            self.save_settings()
            event.accept()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        if event.button() != QtCore.Qt.LeftButton:
            return
        y = event.pos().y()
        h = self.height()
        if h <= 0:
            return
        idx = int((y / h) * 4)
        if event.modifiers() & QtCore.Qt.AltModifier:
            if idx <= 0:
                self.rest_duration = 5 * 60
                if self.phase == "idle" or self.paused:
                    self.set_time_text(self.format_time(self.rest_duration))
            elif idx == 1:
                self.rest_duration = 10 * 60
                if self.phase == "idle" or self.paused:
                    self.set_time_text(self.format_time(self.rest_duration))
            elif idx == 2:
                self.rest_duration = 15 * 60
                if self.phase == "idle" or self.paused:
                    self.set_time_text(self.format_time(self.rest_duration))
            else:
                self.exit_on_work_end = True
        else:
            if idx <= 0:
                self.work_duration = 15 * 60
            elif idx == 1:
                self.work_duration = 30 * 60
            elif idx == 2:
                self.work_duration = 40 * 60
            else:
                self.work_duration = 60 * 60
            if self.phase == "idle" or self.paused:
                self.set_time_text(self.format_time(self.work_duration))
        
        self.save_settings()

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        self.menu_overlay.show_at(event.globalPos())

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, self.always_on_top)
        self.show()
        self.save_settings()

    def play_random_voice(self):
        if not self.random_pool:
            return
        url = QtCore.QUrl.fromLocalFile(random.choice(self.random_pool))
        self.sound_queue.append(url)
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self.start_next_sound()

    def play_category(self, category, default_file=None):
        mapping = {
            'start': self.pool_start,
            'end': self.pool_end,
            'interval': self.pool_interval,
            'resume': self.pool_resume,
            'exit': self.pool_exit,
        }
        pool = mapping.get(category, [])
        season = None
        try:
            season = self.current_season()
        except Exception:
            season = None
        spools = self.seasonal_pools.get(category, {})
        sp = spools.get((season or '').lower(), [])
        tag = None
        try:
            tag = self.current_tag()
        except Exception:
            tag = None
        tpools = getattr(self, 'tag_pools', {}).get(category, {})
        tp = tpools.get((tag or '').lower(), [])
        chosen_pool = tp if tp else (sp if sp else pool)
        if chosen_pool:
            url = QtCore.QUrl.fromLocalFile(random.choice(chosen_pool))
            self.sound_queue.append(url)
            if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self.start_next_sound()
        elif default_file:
            self.play_sound(default_file)

    def build_sound_pool(self):
        self.pool_start = []
        self.pool_end = []
        self.pool_interval = []
        self.pool_resume = []
        self.pool_exit = []
        self.random_pool = []
        self.seasonal_pools = {'start': {}, 'end': {}, 'interval': {}, 'resume': {}, 'exit': {}}
        self.tag_pools = {'start': {}, 'end': {}, 'interval': {}, 'resume': {}, 'exit': {}}
        def add_dir_to(lst, d):
            if os.path.exists(d):
                for fn in os.listdir(d):
                    if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                        lst.append(os.path.join(d, fn))
        base_local = os.path.join(base_dir(), 'sounds')
        base_parent = os.path.join(os.path.dirname(base_dir()), 'sounds')
        # 分类目录
        for root in (base_local, base_parent):
            add_dir_to(self.pool_start, os.path.join(root, 'random', 'start'))
            add_dir_to(self.pool_end, os.path.join(root, 'random', 'end'))
            add_dir_to(self.pool_interval, os.path.join(root, 'random', 'interval'))
            add_dir_to(self.pool_resume, os.path.join(root, 'random', 'resume'))
            add_dir_to(self.pool_exit, os.path.join(root, 'random', 'exit'))
            for cat in ('start', 'end', 'interval', 'resume', 'exit'):
                base_cat = os.path.join(root, 'random', cat)
                if os.path.exists(base_cat):
                    for s in os.listdir(base_cat):
                        sp = os.path.join(base_cat, s)
                        if os.path.isdir(sp):
                            key = s.lower()
                            self.seasonal_pools[cat].setdefault(key, [])
                            for fn in os.listdir(sp):
                                if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                                    self.seasonal_pools[cat][key].append(os.path.join(sp, fn))
                tags_cat = os.path.join(root, 'random', cat, 'tags')
                if os.path.exists(tags_cat):
                    for t in os.listdir(tags_cat):
                        tp = os.path.join(tags_cat, t)
                        if os.path.isdir(tp):
                            key = t.lower()
                            self.tag_pools[cat].setdefault(key, [])
                            for fn in os.listdir(tp):
                                if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                                    self.tag_pools[cat][key].append(os.path.join(tp, fn))
        cloud_root = os.path.join(base_dir(), 'sounds', 'cloud')
        add_dir_to(self.pool_start, os.path.join(cloud_root, 'start'))
        add_dir_to(self.pool_end, os.path.join(cloud_root, 'end'))
        add_dir_to(self.pool_interval, os.path.join(cloud_root, 'interval'))
        add_dir_to(self.pool_resume, os.path.join(cloud_root, 'resume'))
        add_dir_to(self.pool_exit, os.path.join(cloud_root, 'exit'))
        for cat in ('start', 'end', 'interval', 'resume', 'exit'):
            base_cat = os.path.join(cloud_root, cat)
            if os.path.exists(base_cat):
                for s in os.listdir(base_cat):
                    sp = os.path.join(base_cat, s)
                    if os.path.isdir(sp):
                        key = s.lower()
                        self.seasonal_pools[cat].setdefault(key, [])
                        for fn in os.listdir(sp):
                            if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                                self.seasonal_pools[cat][key].append(os.path.join(sp, fn))
            tags_cat = os.path.join(cloud_root, cat, 'tags')
            if os.path.exists(tags_cat):
                for t in os.listdir(tags_cat):
                    tp = os.path.join(tags_cat, t)
                    if os.path.isdir(tp):
                        key = t.lower()
                        self.tag_pools[cat].setdefault(key, [])
                        for fn in os.listdir(tp):
                            if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                                self.tag_pools[cat][key].append(os.path.join(tp, fn))
        # 通用兜底池，支持未分类文件
        add_dir_to(self.random_pool, os.path.join(base_local, 'random'))
        add_dir_to(self.random_pool, os.path.join(base_parent, 'random'))
        add_dir_to(self.random_pool, cloud_root)

    def update_sounds_async(self):
        def worker():
            base_url = os.environ.get('POMODORO_SOUNDS_URL', '').strip()
            if not base_url:
                return
            try:
                # Setup request with User-Agent to avoid blocking by some free hosts
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                
                manifest_url = base_url.rstrip('/') + '/manifest.json'
                req = urllib.request.Request(manifest_url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                
                files = data if isinstance(data, list) else data.get('files', [])
                cloud_root = os.path.join(base_dir(), 'sounds', 'cloud')
                os.makedirs(cloud_root, exist_ok=True)
                
                for item in files:
                    if isinstance(item, str):
                        url = item
                        target_dir = os.path.join(cloud_root, 'start')
                    else:
                        url = item.get('url')
                        cat = (item.get('category') or 'start').lower()
                        if cat not in ('start', 'end', 'ten', 'resume'):
                            cat = 'start'
                        season = (item.get('season') or '').strip().lower()
                        tag = (item.get('tag') or '').strip().lower()
                        if season:
                            target_dir = os.path.join(cloud_root, cat, season)
                        elif tag:
                            target_dir = os.path.join(cloud_root, cat, 'tags', tag)
                        else:
                            target_dir = os.path.join(cloud_root, cat)
                    
                    os.makedirs(target_dir, exist_ok=True)
                    name = os.path.basename(url)
                    dest = os.path.join(target_dir, name)
                    
                    if url and not os.path.exists(dest):
                        try:
                            # Download with headers
                            file_req = urllib.request.Request(url, headers=headers)
                            with urllib.request.urlopen(file_req, timeout=30) as f_src, open(dest, 'wb') as f_dst:
                                f_dst.write(f_src.read())
                        except Exception as e:
                            print(f"Failed to download {name}: {e}")
                            
                self.build_sound_pool()
            except Exception as e:
                print(f"Update check failed: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def current_season(self):
        s = os.environ.get('POMODORO_SEASON', '').strip().lower()
        if s:
            return s
        m = time.localtime().tm_mon
        if m in (3, 4, 5):
            return 'spring'
        if m in (6, 7, 8):
            return 'summer'
        if m in (9, 10, 11):
            return 'autumn'
        return 'winter'

    def current_tag(self):
        t = os.environ.get('POMODORO_TAG', '').strip().lower() or os.environ.get('POMODORO_THEME', '').strip().lower()
        return t

    def env_flag_enabled(self, key, default=True):
        v = os.environ.get(key)
        if v is None:
            return default
        s = str(v).strip().lower()
        return s in ('1', 'true', 'yes', 'on') if default else s not in ('0', 'false', 'no', 'off')

    def toggle_interval_voice(self):
        self.cycle_voice_interval()
        self.menu_overlay.refresh_controls()
        self.apply_phase_visuals()

    def set_voice_interval(self, minutes):
        self.voice_interval_minutes = max(0, int(minutes))

    def cycle_voice_interval(self):
        seq = [10, 15, 30, 0]
        try:
            idx = seq.index(int(self.voice_interval_minutes))
        except ValueError:
            idx = 0
        self.voice_interval_minutes = seq[(idx + 1) % len(seq)]
        self.save_settings()

    def voice_interval_label_text(self):
        m = int(self.voice_interval_minutes or 0)
        if m == 0:
            return "不额外播放语音"
        return f"每{m}分钟播放语音"

    # 间隔语音（分类池优先，空则兜底池）
    def maybe_interval_voice(self):
        interval = int(self.voice_interval_minutes or 0)
        if interval > 0 and self.phase == 'working' and self.elapsed > 0 and self.elapsed % (interval * 60) == 0:
            # Use interval.mp3 as fallback if available, or just ignore if not
            self.play_category('interval', default_file='interval.mp3')

    def play_exit_voice(self):
        if not getattr(self, 'exit_voice_enabled', True):
            return
        
        # Try to play exit voice synchronously (or as close as possible)
        # Since closeEvent kills the app, we need to be careful.
        # However, QMediaPlayer is async.
        # Strategy: play sound, then block for a few seconds or until finished?
        # But we can't easily block for QMediaPlayer signals in a simple function without a loop.
        # Let's try to just play it and delay the close slightly?
        
        # Actually, for "exit" sound, it's better to hide the window and keep the app running until sound finishes.
        # But closeEvent is tricky.
        pass

    def toggle_exit_voice(self):
        self.exit_voice_enabled = not getattr(self, 'exit_voice_enabled', True)
        self.save_settings()

    def closeEvent(self, event):
        if getattr(self, 'exit_voice_enabled', True):
            # If we are already closing (flag?), proceed.
            if getattr(self, '_closing_for_real', False):
                self.save_settings()
                super().closeEvent(event)
                return

            # Initiate exit sequence
            event.ignore()
            
            # Hide the window immediately (looks like it closed)
            self.hide()
            self._closing_for_real = True

            # Use winsound for blocking playback (Windows only)
            # This is much more reliable for exit sounds than QMediaPlayer
            # Find an exit sound file
            sound_file = None
            
            # 1. Try random pool
            if self.pool_exit:
                sound_file = random.choice(self.pool_exit)
            
            # 2. Try default file
            if not sound_file:
                default_path = sound_path('exit.mp3')
                if os.path.exists(default_path):
                    sound_file = default_path
            
            if sound_file:
                print(f"Playing exit sound via winsound: {sound_file}")
                # Play asynchronously first so UI thread isn't totally frozen if we wanted to animate,
                # but here we are exiting, so blocking is actually fine/good.
                # However, winsound.PlaySound doesn't support MP3 well directly? 
                # Wait, winsound only plays WAV! QMediaPlayer plays MP3.
                # Ah, that's the catch.
                
                # If files are MP3, winsound won't work easily without external codec or MCI.
                # Let's try QMediaPlayer again but KEEP THE APP ALIVE properly.
                
                # The issue might be that the run loop is dying or QMediaPlayer is being garbage collected.
                
                # Alternative: Use a separate thread or just block?
                # QMediaPlayer is async.
                
                self.play_category('exit', default_file='exit.mp3')
                
                # Force event loop processing
                loop = QtCore.QEventLoop()
                QtCore.QTimer.singleShot(3000, loop.quit)
                loop.exec()
                
            else:
                print("No exit sound found.")
            
            QtWidgets.QApplication.quit()
            
        else:
            self.save_settings()
            super().closeEvent(event)


def check_resources():
    root = base_dir()
    parent = os.path.dirname(root)
    def has_any(local, parent_path):
        return os.path.exists(local) or os.path.exists(parent_path)
    def audio_count(dir_path):
        if not os.path.exists(dir_path):
            return 0
        c = 0
        for fn in os.listdir(dir_path):
            if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                c += 1
        return c
    print("资源检查")
    imgs = [
        ("idle.png", asset_path("idle.png"), os.path.join(parent, "assets", "idle.png")),
        ("paused.png", asset_path("paused.png"), os.path.join(parent, "assets", "paused.png")),
    ]
    for name, l, p in imgs:
        print(f"图片 {name}: {'OK' if has_any(l, p) else '缺失'}")
    opt_img = ("resume.png", asset_path("resume.png"), os.path.join(parent, "assets", "resume.png"))
    print(f"图片 {opt_img[0]}(可选): {'OK' if has_any(opt_img[1], opt_img[2]) else '缺失'}")
    
    # Check menu icons
    menu_icons = ["pause.png", "stop.png", "reset.png", "setting.png", "pin.png", "voice.png", "exit.png"]
    menu_dir_local = os.path.join(root, "assets", "menu")
    menu_dir_parent = os.path.join(parent, "assets", "menu")
    print("菜单图标(可选，手绘风格):")
    for icon in menu_icons:
        l = os.path.join(menu_dir_local, icon)
        p = os.path.join(menu_dir_parent, icon)
        print(f"  {icon}: {'OK' if has_any(l, p) else '缺失'}")
        
    digits_local = os.path.join(root, "assets", "digits")
    digits_parent = os.path.join(parent, "assets", "digits")
    ddir = digits_local if os.path.exists(digits_local) else digits_parent
    d_ok = os.path.exists(os.path.join(ddir, "0.png")) and os.path.exists(os.path.join(ddir, "colon.png"))
    print(f"手写数字(可选): {'OK' if d_ok else '缺失'}")
    sounds = [
        ("start.mp3", sound_path("start.mp3"), os.path.join(parent, "sounds", "start.mp3")),
        ("end.mp3", sound_path("end.mp3"), os.path.join(parent, "sounds", "end.mp3")),
        ("rest_start.mp3", sound_path("rest_start.mp3"), os.path.join(parent, "sounds", "rest_start.mp3")),
        ("interval.mp3", sound_path("interval.mp3"), os.path.join(parent, "sounds", "interval.mp3")),
        ("resume.mp3", sound_path("resume.mp3"), os.path.join(parent, "sounds", "resume.mp3")),
        ("exit.mp3", sound_path("exit.mp3"), os.path.join(parent, "sounds", "exit.mp3")),
    ]
    for name, l, p in sounds:
        print(f"音频 {name}: {'OK' if has_any(l, p) else '缺失'}")
    cats = ["start", "end", "interval", "resume", "exit"]
    for cat in cats:
        c_local = audio_count(os.path.join(root, "sounds", "random", cat))
        c_parent = audio_count(os.path.join(parent, "sounds", "random", cat))
        print(f"分类池 {cat}: {c_local + c_parent} 个文件")
    cloud_total = 0
    cloud_root = os.path.join(root, "sounds", "cloud")
    if os.path.exists(cloud_root):
        for base, _, files in os.walk(cloud_root):
            for fn in files:
                if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                    cloud_total += 1
    print(f"云端池: {cloud_total} 个文件")


def main():
    if "--check-resources" in sys.argv:
        check_resources()
        return
    app = QtWidgets.QApplication(sys.argv)
    
    # Check/Download resources
    manager = DownloadManager(base_dir())
    
    # We need to keep a reference to the widget so it doesn't get garbage collected
    widgets = []
    
    def start_app():
        w = PomodoroWidget()
        w.show()
        widgets.append(w)
        
    manager.download_complete.connect(start_app)
    manager.start()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
