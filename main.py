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
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
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
        self.image_label.setScaledContents(True)
        self.image_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

        pix = QtGui.QPixmap(resolve_asset("idle.png"))
        
        # Determine initial size
        init_w, init_h = 400, 400
        settings_path = os.path.join(base_dir(), "settings.json")
        loaded_size = False
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if "width" in d and "height" in d:
                        init_w = d["width"]
                        init_h = d["height"]
                        loaded_size = True
            except:
                pass
        
        if not loaded_size and not pix.isNull():
            # If no saved size, use scaled down image size (user said it was too big)
            s = pix.size()
            # Scale to 60% of original, or clamp to 300x300 roughly
            scale_factor = 0.6
            init_w = int(s.width() * scale_factor)
            init_h = int(s.height() * scale_factor)
            
            # Ensure reasonable minimums
            init_w = max(200, init_w)
            init_h = max(200, init_h)

        if not pix.isNull():
            self.image_label.setPixmap(pix)
        
        self.resize(init_w, init_h)

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

        self.animation_frames = []
        self.current_frame_index = 0
        self.animation_timer = QtCore.QTimer(self)
        self.animation_timer.setInterval(100) # 10fps
        self.animation_timer.timeout.connect(self.update_animation)
        self.current_anim_type = "idle" # or "paused"

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
        self.resume_button.setFixedSize(200, 200)
        self.resume_button.setAlignment(QtCore.Qt.AlignCenter)
        self.resume_button.setScaledContents(True)
        rpix = QtGui.QPixmap(resolve_asset("resume.png"))
        if not rpix.isNull():
            self.resume_button.setPixmap(rpix)
        else:
            self.resume_button.setText("继续")
            self.resume_button.setStyleSheet("background: rgba(0,0,0,0.3); color: white; padding:6px; border-radius:6px; font-size: 24px;")
        self.resume_button.hide()
        self.resume_button.mousePressEvent = lambda e: (self.start_or_resume() if e.button() == QtCore.Qt.LeftButton else e.ignore())
        self.resume_offset_y_ratio = 0.08

        self.start_button = QtWidgets.QPushButton("开始", self)
        s_icon = resolve_asset("start_btn.png")
        if os.path.exists(s_icon):
            self.start_button.setText("")
            self.start_button.setIcon(QtGui.QIcon(s_icon))
            # Initial size, will be updated in place_start_button
            self.start_button.setIconSize(QtCore.QSize(80, 80))
            self.start_button.setFixedSize(100, 100)
            self.start_button.setStyleSheet("border: none; background: transparent;")
        else:
            self.start_button.setFixedSize(88, 34)
        self.start_button.clicked.connect(self.start_or_resume)
        self.start_button.show()
        
        # Time background (optional)
        self.time_bg_label = QtWidgets.QLabel(self)
        self.time_bg_label.setScaledContents(True)
        self.time_bg_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        tbg = resolve_asset("time_bg.png")
        if os.path.exists(tbg):
            self.time_bg_label.setPixmap(QtGui.QPixmap(tbg))
        self.time_bg_label.hide() # Hidden by default, shown in place_time_label if asset exists
        # Ensure correct stacking order: Image (bottom) < Time BG < Time Label (top)
        self.image_label.lower()
        self.time_bg_label.stackUnder(self.time_label)

        self.place_start_button()

        # Initialize visuals (load animation or static image)
        self.apply_phase_visuals()
        
        # Enforce scale-down if first run logic didn't catch it but user wants it smaller
        # Heuristic: if current size is very large (e.g. original 400x400 or more) and not loaded from explicit small settings
        if not loaded_size:
             # Already handled above
             pass
        else:
             # Check if we should force resize down for "huge" windows on this update
             # Only if it matches default huge size exactly? 
             # Or better: check if we have a special flag or just do it once?
             # Let's just trust the user request: "Character didn't shrink" -> force it.
             # We can't distinguish "user wants it big" vs "user forgot to resize".
             # But if I force it to 60% of CURRENT size, it might annoy some.
             # However, I'll assume standard use case: 400x400 is too big.
             if self.width() >= 400 and self.height() >= 400:
                 new_w = int(self.width() * 0.6)
                 new_h = int(self.height() * 0.6)
                 self.resize(new_w, new_h)
                 self.image_label.setGeometry(0, 0, new_w, new_h)

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
        
        # Place time background if it exists
        if hasattr(self, 'time_bg_label') and not self.time_bg_label.pixmap().isNull():
            self.time_bg_label.setGeometry(x, y, label_w, label_h)
            self.time_bg_label.show()
            self.time_bg_label.stackUnder(self.time_label) # Ensure it's behind time_label but above image
        
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
        
        # Proportional size for Start Button
        # User request: "Start button too small"
        # Increased ratio to 25% of min dimension
        min_dim = min(w, h)
        btn_size = int(min_dim * 0.25)
        # Relaxed constraints: min 50, max 150
        btn_size = max(50, min(150, btn_size))
        
        self.start_button.setFixedSize(btn_size, btn_size)
        self.start_button.setIconSize(QtCore.QSize(int(btn_size * 0.9), int(btn_size * 0.9)))
        
        bw = self.start_button.width()
        bh = self.start_button.height()
        
        # Margin proportional to window size but tight to corner
        margin = max(5, int(min(w, h) * 0.02)) # 2% margin or 5px
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
        # Determine which visual state we should be in
        target_anim = "idle"
        use_static = False
        
        if self.adjusting_duration:
             # When adjusting, show preview based on mode
             target_anim = "idle" if self.adjust_mode == 'work' else "paused"
             use_static = True # Preview is static for now, or animated? User didn't specify, but static is safer for adjustment
        else:
            if self.phase == "working":
                target_anim = "idle"
                use_static = False
            elif self.phase == "rest":
                target_anim = "paused"
                use_static = False
            elif self.phase == "idle":
                target_anim = "idle"
                use_static = True # User requested static for Start/Idle state
            
            # If paused logic is separate (user clicked pause)
            if self.paused:
                target_anim = "paused"
                use_static = True # User requested static for Paused state

        # Only reload if changed
        current_static = getattr(self, 'current_anim_static', None)
        if target_anim != self.current_anim_type or use_static != current_static or not self.animation_frames:
             self.load_animation_frames(target_anim, force_static=use_static)
        
        # Show/hide resume button based on paused state
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
            
        # Ensure geometry is correct
        self.place_time_label()
        self.place_start_button()

    def load_animation_frames(self, anim_type, force_static=False):
        """
        Load animation frames for 'idle' or 'paused'.
        If force_static is True, prioritize single image 'idle.png' or 'paused.png'.
        Otherwise, prioritize folders 'assets/idle' or 'assets/paused'.
        """
        self.animation_frames = []
        self.current_frame_index = 0
        self.current_anim_type = anim_type
        self.current_anim_static = force_static
        
        # Helper to load single image
        def load_single(name):
            path = resolve_asset(f"{name}.png")
            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                self.animation_frames.append(pix)
                return True
            return False

        loaded = False
        
        # If static requested, try single image first
        if force_static:
            loaded = load_single(anim_type)
            # If failed, try folder but only take first frame
            if not loaded:
                folder_path = resolve_asset(anim_type)
                if os.path.isdir(folder_path):
                     files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith('.png')])
                     if files:
                         pix = QtGui.QPixmap(os.path.join(folder_path, files[0]))
                         if not pix.isNull():
                             self.animation_frames.append(pix)
                             loaded = True

        # If not static or static failed (and fallback above failed), try folder logic
        if not loaded:
            folder_path = resolve_asset(anim_type)
            if os.path.isdir(folder_path):
                files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith('.png')])
                if files:
                    for f in files:
                        pix = QtGui.QPixmap(os.path.join(folder_path, f))
                        if not pix.isNull():
                            self.animation_frames.append(pix)
                    if self.animation_frames:
                        loaded = True
        
        # Fallback to single image if folder empty/missing and we haven't loaded yet
        if not loaded and not force_static:
             loaded = load_single(anim_type)

        # Final fallbacks (cross-type)
        if not self.animation_frames:
             # Try opposite type
             fallback_type = 'idle' if anim_type == 'paused' else 'idle' 
             if fallback_type != anim_type:
                 # Try folder
                 folder_path = resolve_asset(fallback_type)
                 if os.path.isdir(folder_path):
                     files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith('.png')])
                     for f in files:
                         pix = QtGui.QPixmap(os.path.join(folder_path, f))
                         if not pix.isNull():
                             self.animation_frames.append(pix)
                 # Try single
                 if not self.animation_frames:
                     load_single(fallback_type)

        if self.animation_frames:
            # Set initial frame
            self.image_label.setPixmap(self.animation_frames[0])
            # self.resize(self.animation_frames[0].size()) # User requested size persistence
            # self.image_label.setGeometry(0, 0, self.width(), self.height()) # Handled by resizeEvent
            
            # Start timer if more than 1 frame AND not forced static
            if len(self.animation_frames) > 1 and not force_static:
                if not self.animation_timer.isActive():
                    self.animation_timer.start()
            else:
                self.animation_timer.stop()
        else:
            self.animation_timer.stop()
            # If absolutely nothing, keep 400x400 default or whatever
            if self.width() < 100:
                self.resize(400, 400)

    def update_animation(self):
        if not self.animation_frames:
            return
        self.current_frame_index = (self.current_frame_index + 1) % len(self.animation_frames)
        self.image_label.setPixmap(self.animation_frames[self.current_frame_index])

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
                        # self.resize(pix.size()) # Keep current size
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
                        # self.resize(pix.size()) # Keep current size
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
                self.check_updates_enabled = data.get("check_updates_enabled", True)
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
            "check_updates_enabled": getattr(self, "check_updates_enabled", True),
            "sounds_update_url": getattr(self, "sounds_update_url", ""),
            "layout_config": self.layout_config,
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height()
        }
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def resizeEvent(self, event):
        self.image_label.setGeometry(0, 0, self.width(), self.height())
        self.place_time_label()
        self.place_start_button()
        self.place_resume_button()
        if hasattr(self, 'time_bg_label'):
            self.time_bg_label.setGeometry(self.time_label.geometry())
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if not self.adjusting_duration:
                self.dragging = True
                self.drag_offset = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            # Force show menu on right click
            self.menu_overlay.show_at(event.globalPos())
            event.accept()
            return
            
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

    def toggle_check_updates(self):
        self.check_updates_enabled = not getattr(self, "check_updates_enabled", True)
        self.save_settings()

    def toggle_exit_voice(self):
        self.exit_voice_enabled = not getattr(self, 'exit_voice_enabled', True)
        self.save_settings()

    def toggle_check_updates(self):
        self.check_updates_enabled = not getattr(self, "check_updates_enabled", True)
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


def resolve_menu_icon(name):
    # This is from ImageMenu logic, but main.py doesn't have it defined globally.
    # It was in ImageMenu but we need it here for check_resources.
    # Let's import it or duplicate logic.
    # ImageMenu is imported inside PomodoroWidget? No, it's in same file but check_resources is standalone.
    # But wait, ImageMenu is a class in another file `image_menu.py`.
    # We should import it from there.
    from image_menu import resolve_menu_icon as rmi
    return rmi(name)

def check_resources():
    print("资源检查")
    
    # Check images (single or sequence)
    for img in ["idle", "paused"]:
        folder = resolve_asset(img)
        single = resolve_asset(f"{img}.png")
        if os.path.isdir(folder) and any(f.endswith('.png') for f in os.listdir(folder)):
             count = len([f for f in os.listdir(folder) if f.endswith('.png')])
             print(f"图片序列 {img}: OK ({count} frames)")
        elif os.path.exists(single):
             print(f"图片 {img}.png: OK")
        else:
             print(f"图片 {img}: 缺失")

    # Check optional images
    for img in ["resume.png", "start_btn.png"]:
        path = resolve_asset(img)
        if os.path.exists(path):
            print(f"图片 {img}(可选): OK")
        else:
            print(f"图片 {img}(可选): 缺失")
            
    # Check menu icons
    print("菜单图标(可选，手绘风格):")
    for img in ["pause.png", "setting.png", "pin.png", "exit.png", "check.png"]:
        path = resolve_menu_icon(img)
        if path and os.path.exists(path):
             print(f"  {img}: OK")
        else:
             print(f"  {img}: 缺失")
             
    # Check digits
    digits_ok = True
    for i in range(10):
        if not os.path.exists(resolve_asset(f"digits/{i}.png")):
            digits_ok = False
            break
    if digits_ok:
        print("手写数字(可选): OK")
    else:
        print("手写数字(可选): 部分缺失或未启用")
        
    # Check basic sounds
    for snd in ["start.mp3", "end.mp3", "rest_start.mp3", "interval.mp3", "resume.mp3", "exit.mp3"]:
        path = sound_path(snd)
        if os.path.exists(path):
            print(f"音频 {snd}: OK")
        else:
            print(f"音频 {snd}: 缺失 (将使用随机池)")
            
    # Check random pools
    for category in ["start", "end", "interval", "resume", "exit"]:
        d = sound_path(f"random/{category}")
        count = 0
        if os.path.isdir(d):
            count = len([f for f in os.listdir(d) if f.endswith(".mp3")])
        print(f"分类池 {category}: {count} 个文件")

    # Check cloud pool (mock)
    cloud_dir = os.path.join(base_dir(), "cloud")
    count = 0
    if os.path.isdir(cloud_dir):
        count = len([f for f in os.listdir(cloud_dir) if f.endswith(".mp3")])
    print(f"云端池: {count} 个文件")


def main():
    if "--check-resources" in sys.argv:
        check_resources()
        return
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # We need to keep a reference to the widget so it doesn't get garbage collected
    widgets = []
    
    def start_app():
        w = PomodoroWidget()
        w.show()
        widgets.append(w)
        
    # Check settings for update flag
    check_updates = True
    settings_path = os.path.join(base_dir(), "settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                check_updates = d.get("check_updates_enabled", True)
        except Exception:
            pass

    if check_updates:
        # Check/Download resources
        manager = DownloadManager(base_dir())
        manager.download_complete.connect(start_app)
        manager.start()
    else:
        start_app()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
