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


def resolve_path(subfolder, *parts):
    # 1. Check external (user override)
    external = os.path.join(base_dir(), subfolder, *parts)
    if os.path.exists(external):
        return external
    
    # 2. Check bundled (PyInstaller _MEIPASS)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundled = os.path.join(sys._MEIPASS, subfolder, *parts)
        if os.path.exists(bundled):
            return bundled
            
    # 3. Return external as default
    return external


def asset_path(*parts):
    return resolve_path("assets", *parts)


def sound_path(*parts):
    return resolve_path("sounds", *parts)


def resolve_asset(name):
    local = asset_path(name)
    if os.path.exists(local):
        return local
    parent = os.path.join(os.path.dirname(base_dir()), "assets", name)
    return parent if os.path.exists(parent) else local



class TimerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        
        self.main_window = parent
        self.flipped = False
        
        # Time Label
        self.time_label = QtWidgets.QLabel(self)
        self.time_label.setText("00:00")
        self.time_label.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(22)
        font.setBold(True)
        self.time_label.setFont(font)
        self.time_label.setStyleSheet("color: black;")
        
        # Time Background
        self.time_bg_label = QtWidgets.QLabel(self)
        self.time_bg_label.setScaledContents(True)
        self.time_bg_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        tbg = resolve_asset("time_bg.png")
        if os.path.exists(tbg):
            self.time_bg_label.setPixmap(QtGui.QPixmap(tbg))
        self.time_bg_label.hide()
        self.time_bg_label.stackUnder(self.time_label)

        # Digit Container
        self.digit_container = QtWidgets.QWidget(self)
        self.digit_layout = QtWidgets.QHBoxLayout(self.digit_container)
        self.digit_layout.setContentsMargins(0, 0, 0, 0)
        self.digit_layout.setSpacing(0)
        self.digit_labels = [QtWidgets.QLabel(self.digit_container) for _ in range(5)]
        for lbl in self.digit_labels:
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setScaledContents(False)
            self.digit_layout.addWidget(lbl)
        self.digit_container.hide()
        
        self.dragging = False
        self.drag_offset = QtCore.QPoint()
        
        # Layout Config
        self.font_size = 22
        self.adjusting_duration = False
        
        # Initial Resize
        self.update_layout()

    def update_layout(self):
        # Update font
        font = self.time_label.font()
        if font.pointSize() != self.font_size:
            font.setPointSize(self.font_size)
            self.time_label.setFont(font)
        
        self.time_label.adjustSize()
        w = self.time_label.width()
        h = self.time_label.height()
        
        # Ensure minimum size
        w = max(w, 50)
        h = max(h, 20)
        
        self.resize(w, h)
        self.time_label.setGeometry(0, 0, w, h)
        
        if not self.time_bg_label.pixmap().isNull():
            self.time_bg_label.setGeometry(0, 0, w, h)
            self.time_bg_label.show()
            
        self.digit_container.setGeometry(0, 0, w, h)

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
            self.time_label.setText(text)
            self.time_label.hide()
            self.show_digit_time(text)
        else:
            self.digit_container.hide()
            self.time_label.show()
            self.time_label.setText(text)
            self.update_layout() # Resize window to fit text

    def show_digit_time(self, text):
        if text == "INF":
            p = resolve_asset("digits/infinite.png")
            if not os.path.exists(p):
                 p = self.digit_path("infinite") 
            
            pm = QtGui.QPixmap(p)
            if pm.isNull():
                 self.digit_container.hide()
                 self.time_label.setText("∞")
                 self.time_label.show()
                 self.update_layout()
                 return

            for lbl in self.digit_labels:
                lbl.hide()
            
            lbl = self.digit_labels[0]
            lbl.show()
            if self.flipped:
                pm = pm.transformed(QtGui.QTransform().rotate(180))
            lbl.setPixmap(pm)
            lbl.setScaledContents(True)
            
            container_h = self.height()
            container_w = self.width()
            
            aspect = pm.width() / max(1, pm.height())
            target_h = int(container_h * 0.8)
            target_w = int(target_h * aspect)
            
            if target_w > container_w:
                target_w = container_w
                target_h = int(target_w / aspect)
            
            lbl.setFixedSize(target_w, target_h)
            
            self.digit_layout.setContentsMargins(
                (container_w - target_w) // 2, 
                (container_h - target_h) // 2, 
                0, 0
            )
            self.digit_container.show()
            self.digit_container.raise_()
            return

        chars = [text[0], text[1], ":", text[3], text[4]]
        if self.flipped:
            chars = reversed(chars) # Reverse char order for 180 flip

        pixmaps = []
        for ch in chars:
            p = self.digit_path(ch)
            pm = QtGui.QPixmap(p)
            if self.flipped and not pm.isNull():
                pm = pm.transformed(QtGui.QTransform().rotate(180))
            pixmaps.append(pm if not pm.isNull() else QtGui.QPixmap())
        
        container_w = self.width()
        container_h = self.height()
        
        temp_height = container_h
        total_w_at_full_height = 0
        for pm in pixmaps:
            if not pm.isNull():
                total_w_at_full_height += pm.width() * (temp_height / max(1, pm.height()))
            else:
                total_w_at_full_height += temp_height * 0.5
        
        pad_px = temp_height * -0.04
        total_w_at_full_height += pad_px * 5
        
        safe_container_w = container_w * 0.95
        
        if total_w_at_full_height > safe_container_w:
            scale_factor = safe_container_w / total_w_at_full_height
            final_height = int(temp_height * scale_factor)
        else:
            final_height = temp_height
            
        final_height = max(1, int(final_height))
        
        scaled = []
        for pm in pixmaps:
            if pm.isNull():
                scaled.append(QtGui.QPixmap())
            else:
                scaled.append(pm.scaledToHeight(final_height, QtCore.Qt.SmoothTransformation))
                
        for i, spm in enumerate(scaled):
            self.digit_labels[i].setScaledContents(False)
            self.digit_labels[i].setPixmap(spm)
            self.digit_labels[i].setFixedHeight(final_height)
            self.digit_labels[i].show()
            if not spm.isNull():
                self.digit_labels[i].setFixedWidth(spm.width())
            else:
                self.digit_labels[i].setFixedWidth(max(1, int(final_height * 0.5)))
                
        self.digit_layout.setSpacing(int(final_height * -0.04))
        self.digit_layout.setContentsMargins(0, 0, 0, 0)
        
        self.digit_container.show()
        self.digit_container.raise_()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # Control + Drag = Move Timer Position (Independent from character)
            # Default Drag = Adjust Time (Work/Rest duration)
            
            # The user requested: "Time card needs Control to be dragged, now it drags directly"
            # This implies the DEFAULT behavior should NOT be moving the widget.
            # So we swap the logic:
            # Control + Drag = Move Widget Position
            # No Modifier (Default) = Adjust Time
            
            if event.modifiers() & QtCore.Qt.ControlModifier:
                 # Control pressed -> Move the widget
                 self.dragging = True
                 self.drag_offset = event.globalPosition().toPoint() - self.pos()
            else:
                 # No modifier -> Adjust Time duration
                 # Only allowed if idle or paused
                 can_adjust = False
                 if self.main_window:
                     if self.main_window.phase == "idle" or self.main_window.paused:
                         can_adjust = True
                 
                 if can_adjust:
                     self.adjusting_duration = True
                     self.drag_start_pos = event.globalPosition().toPoint()
                     if self.main_window:
                         self.main_window.adjusting_duration = True
                         
                         # Determine mode
                         self.adjust_mode = getattr(self.main_window, 'edit_mode', 'work')
                         if self.adjust_mode == 'rest':
                             self.duration_start = self.main_window.rest_duration
                             # Visual feedback for rest
                             self.main_window.exit_on_work_end = False # Prevent exit during adjustment
                             pix = QtGui.QPixmap(resolve_asset("paused.png"))
                             if not pix.isNull():
                                 self.main_window.image_label.setPixmap(pix)
                                 self.main_window.image_label.resize(self.main_window.width(), self.main_window.height())
                         else:
                             self.duration_start = self.main_window.work_duration
            
            event.accept()
            if self.main_window:
                self.main_window.setFocus()
                
        # Forward right click to main window for menu
        elif event.button() == QtCore.Qt.RightButton:
            if self.main_window:
                self.main_window.menu_overlay.show_at(event.globalPosition().toPoint())
                event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()
            
        elif getattr(self, 'adjusting_duration', False) and self.main_window:
            diff = event.globalPosition().toPoint() - self.drag_start_pos
            dx = diff.x()
            dy = diff.y()
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
                if new_dur != self.main_window.work_duration:
                    self.main_window.work_duration = new_dur
                    self.main_window.set_time_text(self.main_window.format_time(new_dur))
            else:
                new_dur = max(30, min(900, new_dur))
                if new_dur != self.main_window.rest_duration:
                    self.main_window.rest_duration = new_dur
                    self.main_window.set_time_text(self.main_window.format_time(new_dur))
            
            event.accept()
            
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.dragging:
                self.dragging = False
                if self.main_window:
                    offset = self.pos() - self.main_window.pos()
                    self.main_window.layout_config['timer_offset_x'] = offset.x()
                    self.main_window.layout_config['timer_offset_y'] = offset.y()
                    self.main_window.save_settings()
            
            if self.adjusting_duration:
                self.adjusting_duration = False
                if self.main_window:
                    self.main_window.adjusting_duration = False
                    self.main_window.save_settings()
                    # Restore visuals
                    self.main_window.apply_phase_visuals()
            
            event.accept()

    def wheelEvent(self, event):
        # Resize timer font
        if event.modifiers() & QtCore.Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.font_size = min(120, self.font_size + 2)
            else:
                self.font_size = max(8, self.font_size - 2)
            
            self.update_layout()
            if self.main_window:
                self.main_window.save_settings()
            event.accept()
        else:
            # Pass other wheel events to main window (e.g. volume? or char resize?)
            # But main window handles char resize via Shift+Wheel.
            # If we want to support that while hovering timer:
            if self.main_window:
                self.main_window.wheelEvent(event)

    def keyPressEvent(self, event):
        if self.main_window:
            self.main_window.keyPressEvent(event)


class PomodoroWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.image_label = QtWidgets.QLabel(self)
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setScaledContents(True)
        # self.image_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True) # Removed to allow right-click menu

        pix = QtGui.QPixmap(resolve_asset("idle.png"))
        if pix.isNull():
            # Fallback if image fails to load
            self.image_label.setStyleSheet("background-color: rgba(0, 0, 0, 100); color: white; border: 2px dashed white;")
            self.image_label.setText("Image Missing")
        
        # System Tray Icon
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        icon_path = resolve_asset("icon.png")
        if not os.path.exists(icon_path):
             icon_path = resolve_asset("icons/icon.png")
        
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QtGui.QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
            
        tray_menu = QtWidgets.QMenu()
        show_action = tray_menu.addAction("显示/隐藏")
        show_action.triggered.connect(lambda: self.hide() if self.isVisible() else self.show())
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(QtWidgets.QApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Determine initial size
        # Adaptive Size Logic:
        # If settings exist, use them.
        # If not, calculate based on screen resolution (e.g., 35% of screen height).
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
        
        if not loaded_size:
            # Smart Adaptive Sizing
            screen = QtWidgets.QApplication.primaryScreen()
            if screen:
                scr_rect = screen.availableGeometry()
                # Target height: 35% of screen height
                target_h = int(scr_rect.height() * 0.35)
                target_h = max(200, min(800, target_h)) # Clamp reasonable limits
                
                # Calculate width based on aspect ratio
                if not pix.isNull():
                    aspect = pix.width() / max(1, pix.height())
                    target_w = int(target_h * aspect)
                else:
                    target_w = target_h
                
                init_w, init_h = target_w, target_h
        
        if not pix.isNull():
            self.image_label.setPixmap(pix)
        
        self.resize(init_w, init_h)

        self.image_label.setGeometry(0, 0, self.width(), self.height())
        
        # Initialize TimerWidget
        self.timer_widget = TimerWidget(self)
        self.timer_widget.show()
        
        # Layout config
        self.layout_config = {
            "timer_offset_x": 100,
            "timer_offset_y": 100,
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
        self.edit_mode = 'work'
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.duration_start = self.work_duration
        self.exit_on_work_end = False
        self.is_flipped = False

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
        self.holiday_pools = {}
        self.ten_voice_enabled = self.env_flag_enabled('POMODORO_TEN_ENABLE', default=True)
        self.voice_interval_minutes = 10
        
        # Cheat Code Buffer
        self.cheat_buffer = ""
        self.cheat_timer = QtCore.QTimer(self)
        self.cheat_timer.setInterval(5000) # Reset buffer after 5 seconds of inactivity
        self.cheat_timer.setSingleShot(True)
        self.cheat_timer.timeout.connect(self.reset_cheat_buffer)
        
        self.load_calendar_config()
        self.build_sound_pool()
        self.update_sounds_async()

        self.load_settings()

        self.dragging = False
        self.drag_offset = QtCore.QPoint()

        # 确保初始几何同步
        self.place_time_label()

        self.set_time_text(self.format_time(self.work_duration))
        self.menu_overlay = ImageMenu(self)
        if 'menu_scale' in self.layout_config:
            self.menu_overlay.set_scale(self.layout_config['menu_scale'])

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
        # self.image_label was already initialized at the beginning of __init__
        # Do not re-initialize it here, otherwise the loaded image will be lost.
        
        # Ensure image label fills the window initially
        self.image_label.setGeometry(0, 0, self.width(), self.height())
        self.image_label.lower()

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
        
        # Ensure correct stacking order
        self.image_label.lower()
        self.timer_widget.raise_()
        self.start_button.raise_()

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
        
        # Initial icon update
        self.update_app_icon()
        
        # Check for holiday greeting (delayed to ensure app is ready)
        # Note: update_app_icon is also called inside check_holiday_greeting
        QtCore.QTimer.singleShot(2000, self.check_holiday_greeting)

    def update_app_icon(self):
        """Update application icon based on active holidays or seasons."""
        icon_path = None
        
        # Helper to check for icon in assets/icons/ folder
        def get_icon_path(name):
            # Try assets/icons/name.png
            p = resolve_asset(f"icons/{name}.png")
            if os.path.exists(p):
                return p
            # Fallback to old style assets/icon_name.png (optional, but good for compatibility)
            p = resolve_asset(f"icon_{name}.png")
            if os.path.exists(p):
                return p
            return None

        # 1. Check Holidays (Priority)
        holidays = self.get_active_holidays()
        if holidays:
            # Try finding an icon for the first active holiday
            # e.g. assets/icons/birthday.png
            for h in holidays:
                p = get_icon_path(h)
                if p:
                    icon_path = p
                    break
        
        # 2. Check Seasons (Secondary)
        if not icon_path:
            seasons = self.get_active_seasons()
            if seasons:
                for s in seasons:
                    p = get_icon_path(s)
                    if p:
                        icon_path = p
                        break
        
        # 3. Default
        if not icon_path:
            # Try assets/icons/default.png or assets/icons/icon.png
            p = resolve_asset("icons/default.png")
            if not os.path.exists(p):
                p = resolve_asset("icons/icon.png")
            if not os.path.exists(p):
                p = resolve_asset("icon.png")
            
            if os.path.exists(p):
                icon_path = p
            
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

    def place_time_label(self):
        # Update timer widget config if needed
        cfg = getattr(self, 'layout_config', {})
        
        # Restore font size
        f_size = cfg.get("font_size", 22)
        if self.timer_widget.font_size != f_size:
            self.timer_widget.font_size = f_size
            self.timer_widget.update_layout()
            
        # Position
        off_x = cfg.get("timer_offset_x", 100)
        off_y = cfg.get("timer_offset_y", 100)
        
        # Ensure initial valid position if it was never set (e.g. first run with new code)
        # If we migrated from relative, we might need to calculate it.
        # But we replaced the config loading. If loading old config, it has time_x/time_y.
        # We should migrate it.
        if "timer_offset_x" not in cfg and "time_x" in cfg:
            # Migrate
            off_x = int(self.width() * cfg["time_x"])
            off_y = int(self.height() * cfg["time_y"])
            self.layout_config["timer_offset_x"] = off_x
            self.layout_config["timer_offset_y"] = off_y
        
        self.timer_widget.move(self.x() + off_x, self.y() + off_y)


    def place_resume_button(self):
        w = self.width()
        h = self.height()
        
        # Resize to be small and in top-right (smaller than start button)
        min_dim = min(w, h)
        # User request: Increase 1.5x (from 0.15 -> 0.225), "can be even bigger" -> 0.30
        btn_size = int(min_dim * 0.30)
        btn_size = max(60, min(160, btn_size))
        
        self.resume_button.setFixedSize(btn_size, btn_size)
        
        bw = self.resume_button.width()
        bh = self.resume_button.height()
        
        # Place in top right, similar to start button
        margin = max(5, int(min(w, h) * 0.02))
        rx = max(0, w - bw - margin)
        ry = margin
        self.resume_button.setGeometry(rx, ry, bw, bh)
        self.resume_button.raise_()

    def reset_cheat_buffer(self):
        self.cheat_buffer = ""

    def reset_timer_state(self):
        """Reset timer to initial state without deleting settings."""
        if hasattr(self, 'context_menu') and self.context_menu:
            self.context_menu.close()

        if self.is_flipped:
            self.toggle_flip() # Reset flip state if active
            
        self.tick_timer.stop()
        self.phase = "idle"
        self.paused = False
        self.elapsed = 0
        self.start_button.show()
        self.resume_button.hide()
        
        # Reset text
        self.set_time_text(self.format_time(self.work_duration))
        
        # Apply idle visuals
        self.apply_phase_visuals()
        
        # Clear sound queue
        self.sound_queue.clear()
        self.player.stop()

    def check_cheat_code(self):
        cmd = self.cheat_buffer.lower()
        if cmd.endswith("/remake"):
            self.reset_timer_state()
            self.cheat_buffer = ""
            if self.menu_overlay:
                self.menu_overlay.close()
            return
        if cmd.endswith("/666"):
            self.toggle_flip()
            self.cheat_buffer = ""
            if self.menu_overlay:
                self.menu_overlay.close()
            return
        if "/bir" in cmd:
            # Clean up command for easier parsing (allow spaces)
            clean_cmd = cmd.replace(" ", "")
            if "/bir" in clean_cmd:
                idx = clean_cmd.rfind("/bir")
                suffix = clean_cmd[idx+4:]
                if len(suffix) >= 4 and suffix[:4].isdigit():
                    self.set_birthday(suffix[:4])
                    self.cheat_buffer = ""
                    if self.menu_overlay:
                        self.menu_overlay.close()
                    return

    def toggle_flip(self):
        self.is_flipped = not self.is_flipped
        if hasattr(self, 'timer_widget'):
            self.timer_widget.flipped = self.is_flipped
            # Force update timer display
            self.timer_widget.show_digit_time(self.time_label.text() if hasattr(self, 'time_label') else self.format_time(self.work_duration if self.phase == "working" else (self.rest_duration if self.phase == "rest" else self.work_duration)))
            # Actually we don't track current text in main_window except when updating.
            # But timer_widget has 'set_time_text'. We need to re-trigger it.
            # We can just call update_animation which will eventually refresh visuals, but timer text needs explicit refresh.
            # Best way: Read current text from timer_widget labels? No.
            # Recalculate text based on state.
            
            # Simple hack: force refresh based on elapsed/duration
            remaining = 0
            if self.phase == "working":
                remaining = max(0, self.work_duration - self.elapsed)
            elif self.phase == "rest":
                remaining = max(0, self.rest_duration - self.elapsed)
            else:
                remaining = self.work_duration # Idle
            
            if self.exit_on_work_end and self.phase == "rest":
                 self.set_time_text("INF")
            else:
                 self.set_time_text(self.format_time(remaining))

        # Reload animation frames to apply rotation
        self.load_animation_frames(self.current_anim_type, force_static=self.current_anim_static)
        # Force update current frame
        if self.animation_frames:
            self.image_label.setPixmap(self.animation_frames[self.current_frame_index])

    def reset_settings(self):
        settings_path = os.path.join(base_dir(), "settings.json")
        if os.path.exists(settings_path):
            try:
                os.remove(settings_path)
            except:
                pass
        QtCore.QProcess.startDetached(sys.executable, sys.argv)
        QtWidgets.QApplication.quit()

    def set_birthday(self, date_str):
        self.birthday = date_str
        self.save_settings()
        # self.play_category('start') 
        self.update_app_icon() 

    def keyPressEvent(self, event):
        text = event.text()
        
        # Check if we are currently buffering a cheat code
        if self.cheat_buffer:
            # If Enter/Return is pressed, try to execute the command
            if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
                self.check_cheat_code()
                self.cheat_buffer = "" # Reset buffer after execution attempt
                event.accept()
                return
            
            # Continue buffering valid characters
            if text and text.isprintable():
                self.cheat_buffer += text
                self.cheat_timer.start()
                event.accept()
                return

        # Start buffering if '/' is pressed and not currently buffering
        if text == '/':
            self.cheat_buffer = text
            self.cheat_timer.start()
            event.accept()
            return

        # Normal shortcut handling (Space for Pause/Resume)
        if event.key() == QtCore.Qt.Key_Space and self.isActiveWindow():
            if self.phase == "idle":
                self.start_or_resume()
            elif self.paused:
                self.start_or_resume()
            else:
                # Working or Rest running -> Pause
                self.pause_timer()
            event.accept()
            return

        if event.key() == QtCore.Qt.Key_Alt:
             # Only toggle if idle or paused, and window is active
             if (self.phase == "idle" or self.paused) and self.isActiveWindow():
                 # Toggle edit mode
                 current_mode = getattr(self, 'edit_mode', 'work')
                 self.edit_mode = 'rest' if current_mode == 'work' else 'work'
                 
                 # Update display immediately
                 if self.edit_mode == 'rest':
                     if self.exit_on_work_end:
                         self.set_time_text("INF")
                     else:
                         self.set_time_text(self.format_time(self.rest_duration))
                 else:
                     self.set_time_text(self.format_time(self.work_duration))
                 
                 # Force update visuals (background image) to reflect mode
                 self.apply_phase_visuals()

        super().keyPressEvent(event)

    def place_start_button(self):
        w = self.width()
        h = self.height()
        
        # Proportional size for Start Button
        # User request: Increase 1.5x (from 0.25 -> 0.375)
        min_dim = min(w, h)
        btn_size = int(min_dim * 0.375)
        # Relaxed constraints: min 75, max 225
        btn_size = max(75, min(225, btn_size))
        
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
        # Shift+Wheel to resize window
        if event.modifiers() & QtCore.Qt.ShiftModifier:
            delta = event.angleDelta().y()
            # Scale factor: 10% per scroll step (usually 120 delta)
            step = delta / 1200.0 
            factor = 1.0 + step
            
            # 1. Resize Main Window
            new_w = int(self.width() * factor)
            new_h = int(self.height() * factor)
            
            # Clamp size
            new_h = max(200, min(1200, new_h))
            
            # Calculate width based on aspect ratio of current image or just scale uniformly
            # We want to maintain current aspect ratio of the window
            ratio = self.width() / max(1, self.height())
            new_w = int(new_h * ratio)
            
            self.resize(new_w, new_h)

            # 2. Resize Timer Widget
            # Scale font proportionally
            current_font = self.timer_widget.font_size
            # Use float calculation to avoid getting stuck at small integers, but store as int
            # Better: scale based on window height ratio change if factor is too small?
            # But factor is fine.
            new_font = int(current_font * factor)
            if new_font == current_font and factor != 1.0:
                 # Force at least 1 unit change if factor suggests it
                 if factor > 1: new_font += 1
                 else: new_font -= 1
            
            new_font = max(8, min(200, new_font))
            
            if new_font != current_font:
                self.timer_widget.font_size = new_font
                self.timer_widget.update_layout()
                self.layout_config['font_size'] = new_font

            # 3. Resize Image Menu
            current_scale = getattr(self.menu_overlay, 'ui_scale', 1.0)
            new_scale = current_scale * factor
            new_scale = max(0.5, min(5.0, new_scale))
            
            if abs(new_scale - current_scale) > 0.01:
                self.menu_overlay.set_scale(new_scale)
                self.layout_config['menu_scale'] = new_scale
            
            self.save_settings()
            event.accept()
            return

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

    def set_time_text(self, text):
        self.timer_widget.set_time_text(text)


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
        self.setFocus()

    def pause_timer(self):
        if self.tick_timer.isActive():
            self.tick_timer.stop()
            self.paused = True
            self.apply_phase_visuals()
            self.setFocus()

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
            # self.play_sound("rest_start.mp3") # User confirmed this resource does not exist
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
             # When dragging, show preview based on mode
             target_anim = "idle" if self.adjust_mode == 'work' else "paused"
             use_static = True
        else:
            if self.phase == "working":
                target_anim = "idle"
                use_static = False
            elif self.phase == "rest":
                target_anim = "paused"
                use_static = False
            elif self.phase == "idle":
                # Idle (Waiting to Start)
                # Visual depends on edit_mode: Work -> Idle Visual, Rest -> Paused Visual
                target_anim = "idle" if self.edit_mode == 'work' else "paused"
                use_static = True
            
            # If paused (Paused from Work)
            if self.paused:
                # Paused state
                # Visual depends on edit_mode: Work -> Idle Visual, Rest -> Paused Visual
                # Note: Traditionally Paused used 'paused' visual, but if we are editing work time,
                # we should show 'idle' (work) visual to indicate what we are editing.
                target_anim = "idle" if self.edit_mode == 'work' else "paused"
                use_static = True

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

        # Apply flip if needed
        if self.is_flipped:
            new_frames = []
            for pix in self.animation_frames:
                new_frames.append(pix.transformed(QtGui.QTransform().rotate(180)))
            self.animation_frames = new_frames

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



    def moveEvent(self, event):
        self.place_time_label() # Sync timer position
        super().moveEvent(event)



    def load_calendar_config(self):
        config_path = os.path.join(base_dir(), "calendar_config.json")
        default_config = {
            "seasons": [
                {"id": "spring", "months": [3, 4, 5]},
                {"id": "summer", "months": [6, 7, 8]},
                {"id": "autumn", "months": [9, 10, 11]},
                {"id": "winter", "months": [12, 1, 2]},
                {"id": "winter_vacation", "months": [1, 2]},
                {"id": "summer_vacation", "months": [7, 8]}
            ],
            "holidays": [
                {"id": "christmas", "month": 12, "days": [24, 25, 26]}
            ]
        }
        
        self.calendar_config = default_config
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    if user_config:
                        # Allow partial override? No, replace sections if they exist.
                        if "seasons" in user_config:
                            self.calendar_config["seasons"] = user_config["seasons"]
                        if "holidays" in user_config:
                            self.calendar_config["holidays"] = user_config["holidays"]
            except Exception as e:
                print(f"Failed to load calendar config: {e}")

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
                self.last_greeting_date = data.get("last_greeting_date", "")
                self.birthday = data.get("birthday", "")
                self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, self.always_on_top)
                if hasattr(self, 'timer_widget'):
                    self.timer_widget.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, self.always_on_top)
                    self.timer_widget.show()
                
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
            "last_greeting_date": getattr(self, "last_greeting_date", ""),
            "birthday": getattr(self, "birthday", ""),
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


    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == QtCore.Qt.LeftButton:
            if not self.adjusting_duration:
                self.dragging = True
                self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            # Force show menu on right click
            self.menu_overlay.show_at(event.globalPosition().toPoint())
            event.accept()
            return
            
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
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
            
        # Only allow time adjustment when idle or paused
        if self.phase != "idle" and not self.paused:
            return

        y = event.pos().y()
        h = self.height()
        if h <= 0:
            return
        idx = int((y / h) * 4)
        
        # Use edit_mode instead of modifiers
        mode = getattr(self, 'edit_mode', 'rest')
        
        if mode == 'rest':
            if idx <= 0:
                self.rest_duration = 5 * 60
                self.exit_on_work_end = False
            elif idx == 1:
                self.rest_duration = 10 * 60
                self.exit_on_work_end = False
            elif idx == 2:
                self.rest_duration = 15 * 60
                self.exit_on_work_end = False
            else:
                self.exit_on_work_end = not self.exit_on_work_end
                # Force refresh to show infinite symbol if needed
                if self.phase == "idle" or self.paused:
                    if self.exit_on_work_end:
                        self.set_time_text("INF")
                    else:
                        self.set_time_text(self.format_time(self.rest_duration))
                self.save_settings()
                return

            if self.phase == "idle" or self.paused:
                if self.exit_on_work_end:
                     self.set_time_text("INF")
                else:
                     self.set_time_text(self.format_time(self.rest_duration))
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
        # self.menu_overlay.show_at(event.globalPos())
        self.menu_overlay.show_at(event.globalPos())
        # The menu_overlay (ImageMenu) will take focus and forward keys to us.


    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, self.always_on_top)
        if hasattr(self, 'timer_widget'):
            self.timer_widget.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, self.always_on_top)
            self.timer_widget.show()
        self.show()
        self.save_settings()

    def toggle_check_updates(self):
        self.check_updates_enabled = not getattr(self, "check_updates_enabled", True)
        self.save_settings()

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
            if hasattr(self, 'menu_overlay') and self.menu_overlay:
                self.menu_overlay.close()
            if hasattr(self, 'timer_widget'):
                self.timer_widget.hide()
                self.timer_widget.close()
                self.timer_widget.deleteLater()
                self.timer_widget = None
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
        
        # 1. Prepare candidate pools
        base_pool = list(mapping.get(category, []))
        season_pool = []
        holiday_pool = []

        # Get Season Sounds (Multiple seasons supported)
        active_seasons = self.get_active_seasons()
        spools = self.seasonal_pools.get(category, {})
        
        for s in active_seasons:
            sp = spools.get(s, [])
            if sp:
                season_pool.extend(sp)

        # Get Holiday Sounds (Multiple holidays supported)
        active_holidays = self.get_active_holidays()
        
        for h in active_holidays:
            # From seasonal_pools (e.g. random/start/christmas)
            hp = spools.get(h, [])
            if hp:
                holiday_pool.extend(hp)
            
            # From global holiday pools (e.g. sounds/holidays/christmas)
            h_sounds = self.holiday_pools.get(h, {}).get('common', [])
            if h_sounds:
                holiday_pool.extend(h_sounds)

        # 2. Determine Strategy
        final_pool = []
        
        # Track holiday playback state per day
        # Structure: self.holiday_play_state = {'date': '2023-12-27', 'cats': set()}
        if not hasattr(self, 'holiday_play_state'):
            self.holiday_play_state = {'date': '', 'cats': set()}
            
        today_str = QtCore.QDate.currentDate().toString("yyyy-MM-dd")
        
        # Reset if date changed
        if self.holiday_play_state['date'] != today_str:
            self.holiday_play_state = {'date': today_str, 'cats': set()}
            
        if active_holidays and holiday_pool:
            if category not in self.holiday_play_state['cats']:
                # First time today for this category -> Exclusive Holiday
                final_pool = holiday_pool
                self.holiday_play_state['cats'].add(category)
            else:
                # Subsequent times -> Mix everything
                final_pool = base_pool + season_pool + holiday_pool
        else:
            # No holiday or no holiday sounds -> Standard Mix
            final_pool = base_pool + season_pool

        # 3. Tag Override (Highest Priority)
        tag = None
        try:
            tag = self.current_tag()
        except Exception:
            tag = None
        tpools = getattr(self, 'tag_pools', {}).get(category, {})
        tp = tpools.get((tag or '').lower(), [])
        
        # If tag exists, it overrides everything else
        chosen_pool = tp if tp else final_pool
        
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
            # NEW: Merge 'random' into root categories.
            # Support sounds/start/*.mp3 AND sounds/start.mp3 (legacy)
            
            # 1. Scan folders like sounds/start/
            add_dir_to(self.pool_start, os.path.join(root, 'start'))
            add_dir_to(self.pool_end, os.path.join(root, 'end'))
            add_dir_to(self.pool_interval, os.path.join(root, 'interval'))
            add_dir_to(self.pool_resume, os.path.join(root, 'resume'))
            add_dir_to(self.pool_exit, os.path.join(root, 'exit'))

            # 2. Check for legacy single files like sounds/start.mp3 and add to pool
            for cat, pool in [
                ('start', self.pool_start), 
                ('end', self.pool_end), 
                ('interval', self.pool_interval), 
                ('resume', self.pool_resume), 
                ('exit', self.pool_exit)
            ]:
                single_file = os.path.join(root, f"{cat}.mp3")
                if os.path.exists(single_file) and single_file not in pool:
                    pool.append(single_file)

            for cat in ('start', 'end', 'interval', 'resume', 'exit'):
                base_cat = os.path.join(root, cat)
                if os.path.exists(base_cat):
                    for s in os.listdir(base_cat):
                        sp = os.path.join(base_cat, s)
                        if os.path.isdir(sp):
                            # Skip 'tags' as it is reserved
                            if s.lower() == 'tags':
                                continue
                                
                            key = s.lower()
                            self.seasonal_pools[cat].setdefault(key, [])
                            for fn in os.listdir(sp):
                                if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                                    self.seasonal_pools[cat][key].append(os.path.join(sp, fn))
                                    
                tags_cat = os.path.join(root, cat, 'tags')
                if os.path.exists(tags_cat):
                    for t in os.listdir(tags_cat):
                        tp = os.path.join(tags_cat, t)
                        if os.path.isdir(tp):
                            key = t.lower()
                            self.tag_pools[cat].setdefault(key, [])
                            for fn in os.listdir(tp):
                                if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                                    self.tag_pools[cat][key].append(os.path.join(tp, fn))
                                    
        # Scan Cloud Directory (No Copy Strategy)
        cloud_root = os.path.join(base_dir(), 'cloud')
        if os.path.exists(cloud_root):
            add_dir_to(self.pool_start, os.path.join(cloud_root, 'start'))
            add_dir_to(self.pool_end, os.path.join(cloud_root, 'end'))
            add_dir_to(self.pool_interval, os.path.join(cloud_root, 'interval'))
            add_dir_to(self.pool_resume, os.path.join(cloud_root, 'resume'))
            add_dir_to(self.pool_exit, os.path.join(cloud_root, 'exit'))
            
            for cat in ('start', 'end', 'interval', 'resume', 'exit'):
                base_cat = os.path.join(cloud_root, cat)
                if os.path.exists(base_cat):
                    # Scan for seasonal subfolders (direct children that are not 'tags')
                    for s in os.listdir(base_cat):
                        sp = os.path.join(base_cat, s)
                        if os.path.isdir(sp) and s.lower() != 'tags':
                            key = s.lower()
                            self.seasonal_pools[cat].setdefault(key, [])
                            for fn in os.listdir(sp):
                                if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                                    self.seasonal_pools[cat][key].append(os.path.join(sp, fn))
                                    
                    # Scan for tags
                    tags_cat = os.path.join(base_cat, 'tags')
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
        
        # Load Holiday Sounds
        base_holidays = os.path.join(base_dir(), 'sounds', 'holidays')
        parent_holidays = os.path.join(os.path.dirname(base_dir()), 'sounds', 'holidays')
        
        for root in (base_holidays, parent_holidays):
            if os.path.exists(root):
                for h in os.listdir(root):
                    h_path = os.path.join(root, h)
                    if os.path.isdir(h_path):
                        self.holiday_pools.setdefault(h, {'common': [], 'greeting': []})
                        
                        # Load common (root of holiday folder)
                        for fn in os.listdir(h_path):
                            fp = os.path.join(h_path, fn)
                            if os.path.isfile(fp) and fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                                self.holiday_pools[h]['common'].append(fp)
                                
                        # Load greeting
                        g_path = os.path.join(h_path, 'greeting')
                        if os.path.isdir(g_path):
                            for fn in os.listdir(g_path):
                                if fn.lower().endswith(('.mp3', '.wav', '.ogg')):
                                    self.holiday_pools[h]['greeting'].append(os.path.join(g_path, fn))

    def update_sounds_async(self):
        def worker():
            base_url = os.environ.get('POMODORO_SOUNDS_URL', '').strip()
            if not base_url:
                base_url = getattr(self, 'sounds_update_url', '').strip()
            
            if not base_url:
                return

            # Git support
            if base_url.endswith('.git'):
                cloud_root = os.path.join(base_dir(), 'cloud')
                if os.path.isdir(os.path.join(cloud_root, '.git')):
                    try:
                        import subprocess
                        # Check git presence
                        subprocess.check_call(['git', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        # Pull
                        subprocess.check_call(['git', 'pull'], cwd=cloud_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self.build_sound_pool()
                    except Exception as e:
                        print(f"Git background update failed: {e}")
                return
                
            try:
                # Setup request with User-Agent to avoid blocking by some free hosts
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                
                if base_url.lower().endswith('.json'):
                    manifest_url = base_url
                else:
                    manifest_url = base_url.rstrip('/') + '/manifest.json'
                    
                req = urllib.request.Request(manifest_url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                
                files = data if isinstance(data, list) else data.get('files', [])
                
                # Use cloud folder for downloaded assets
                cloud_root = os.path.join(base_dir(), 'cloud')
                os.makedirs(cloud_root, exist_ok=True)
                
                for item in files:
                    if isinstance(item, str):
                        url = item
                        target_dir = os.path.join(cloud_root, 'start')
                    else:
                        url = item.get('url')
                        cat = (item.get('category') or 'start').lower()
                        
                        if cat == 'holiday':
                            h = (item.get('holiday') or 'unknown').strip().lower()
                            t = (item.get('type') or 'common').strip().lower()
                            target_dir = os.path.join(cloud_root, 'holidays', h, t)
                        else:
                            # Standard categories
                            if cat not in ('start', 'end', 'ten', 'resume', 'exit', 'interval'):
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

    def get_active_seasons(self):
        # Override via Env
        s = os.environ.get('POMODORO_SEASON', '').strip().lower()
        if s:
            return [s]

        active = []
        d = QtCore.QDate.currentDate()
        m = d.month()
        
        seasons = self.calendar_config.get("seasons", [])
        for season in seasons:
            if m in season.get("months", []):
                active.append(season.get("id"))
            
        return active

    def get_active_holidays(self):
        active = []
        d = QtCore.QDate.currentDate()
        m = d.month()
        day = d.day()
        
        # Birthday Check
        if hasattr(self, 'birthday') and self.birthday and len(self.birthday) == 4:
             try:
                 b_m = int(self.birthday[:2])
                 b_d = int(self.birthday[2:])
                 if m == b_m and day == b_d:
                     active.append('birthday')
             except:
                 pass
        
        holidays = self.calendar_config.get("holidays", [])
        for h in holidays:
            if h.get("month") == m and day in h.get("days", []):
                active.append(h.get("id"))
            
        return active

    def check_holiday_greeting(self):
        # Update icon daily
        self.update_app_icon()

        holidays = self.get_active_holidays()
        if not holidays:
            return

        today_str = QtCore.QDate.currentDate().toString("yyyy-MM-dd")
        last = getattr(self, 'last_greeting_date', "")
        
        if last != today_str:
            # Play greeting for the first active holiday found (Priority order: birthday > others)
            # Since get_active_holidays appends in order, the first one is usually the most specific/important if we ordered well.
            # But here we append birthday first, so it's priority 1.
            
            # Find a pool that has greeting
            greeting_pool = []
            
            for h in holidays:
                 p = self.holiday_pools.get(h, {}).get('greeting', [])
                 if not p:
                     p = self.holiday_pools.get(h, {}).get('common', [])
                 if p:
                     greeting_pool.extend(p)
            
            if greeting_pool:
                # Pick one from the mixed greeting pool (if multiple holidays)
                # Or prioritize? Let's random mix.
                url = QtCore.QUrl.fromLocalFile(random.choice(greeting_pool))
                self.sound_queue.insert(0, url)
                if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                    self.start_next_sound()
                
                self.last_greeting_date = today_str
                self.save_settings()

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
