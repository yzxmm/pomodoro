from PySide6 import QtCore, QtGui, QtWidgets
import os
from utils import base_dir, resolve_asset

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
            # Ctrl + Drag = Move Timer Position
            # Default Drag = Adjust Time (Work/Rest duration)
            
            if event.modifiers() & QtCore.Qt.ControlModifier:
                 # Ctrl pressed -> Move the widget
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
                # Use global position for menu
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
                new_dur = max(600, min(3600, new_dur)) # Work: 10m - 1h
            else:
                new_dur = max(30, min(1800, new_dur)) # Rest: 30s - 30m
                
            if self.adjust_mode == 'work':
                if new_dur != self.main_window.work_duration:
                    self.main_window.work_duration = new_dur
                    self.main_window.set_time_text(self.main_window.format_time(new_dur))
            else:
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
        # Ctrl + Wheel = Resize timer font (Time Card Only)
        if event.modifiers() & QtCore.Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.font_size = min(120, self.font_size + 2)
            else:
                self.font_size = max(8, self.font_size - 2)
            
            self.update_layout()
            if self.main_window:
                self.main_window.layout_config['font_size'] = self.font_size
                self.main_window.save_settings()
            event.accept()
        else:
            # Pass other wheel events to main window (e.g. Shift + Wheel for global scaling)
            if self.main_window:
                self.main_window.wheelEvent(event)

    def keyPressEvent(self, event):
        if self.main_window:
            self.main_window.keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Time card should not handle double click zones (Global Requirements L66: Double Click Character Range)
        # Pass to main window or ignore to avoid "messy" interaction
        event.ignore()
