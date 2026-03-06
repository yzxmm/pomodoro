from PySide6 import QtCore, QtGui, QtWidgets
import os
from utils import base_dir, resolve_asset

class TimerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # [Fix] Restore Qt.Tool flag to ensure it always floats above the main character window
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        
        self.main_window = parent
        self.flipped = False
        
        # [Initial Sync] Always stay on top if main window does
        if self.main_window:
             self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, self.main_window.always_on_top)
        
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
        self.bg_aspect_ratio = 3.0 # Default fallback
        if os.path.exists(tbg):
            pix = QtGui.QPixmap(tbg)
            if not pix.isNull():
                self.time_bg_label.setPixmap(pix)
                self.bg_aspect_ratio = pix.width() / max(1, pix.height())
        self.time_bg_label.hide()
        self.time_bg_label.stackUnder(self.time_label)

        # Digit Container
        self.digit_container = QtWidgets.QWidget(self)
        self.digit_labels = [QtWidgets.QLabel(self.digit_container) for _ in range(5)]
        for lbl in self.digit_labels:
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setScaledContents(False)
        self.digit_container.hide()
        
        self.dragging = False
        self.drag_offset = QtCore.QPoint()
        
        # Layout Config
        self.font_size = 22
        self.adjusting_duration = False
        
        # Initial Resize
        self.update_layout()

    def update_layout(self):
        # Use float for smoother scaling if possible
        font = self.time_label.font()
        if hasattr(font, 'setPointSizeF'):
            if abs(font.pointSizeF() - self.font_size) > 0.1:
                font.setPointSizeF(float(self.font_size))
                self.time_label.setFont(font)
        else:
            if font.pointSize() != int(self.font_size):
                font.setPointSize(int(self.font_size))
                self.time_label.setFont(font)
        
        # Determine target height based on font size
        # This keeps the background size tied to the digit size
        h = int(self.font_size * 2.5) 
        w = int(h * self.bg_aspect_ratio)
        
        # Ensure minimum size
        w = max(w, 50)
        h = max(h, 20)
        
        if self.width() != w or self.height() != h:
            self.resize(w, h)
        
        self.time_label.setGeometry(0, 0, w, h)
        
        if not self.time_bg_label.pixmap().isNull():
            self.time_bg_label.setGeometry(0, 0, w, h)
            self.time_bg_label.show()
            
        self.digit_container.setGeometry(0, 0, w, h)
        
        # [Fix] Sync digits immediately with the new background size
        # This prevents the "independent scaling" look where background scales but digits wait for a tick.
        if self.digits_available():
            self.show_digit_time(self.time_label.text())

    def digits_available(self):
        # Cache this or check once
        if hasattr(self, '_digits_available_cache'):
             return self._digits_available_cache
             
        local_dir = os.path.join(base_dir(), "assets", "digits")
        parent_dir = os.path.join(os.path.dirname(base_dir()), "assets", "digits")
        check_dir = local_dir if os.path.exists(local_dir) else parent_dir
        res = os.path.exists(os.path.join(check_dir, "0.png")) and os.path.exists(os.path.join(check_dir, "colon.png"))
        self._digits_available_cache = res
        return res

    def digit_path(self, ch):
        name = "colon.png" if ch == ":" else f"{ch}.png"
        if ch == "infinite": name = "infinite.png"
        
        local = os.path.join(base_dir(), "assets", "digits", name)
        if os.path.exists(local):
            return local
        parent = os.path.join(os.path.dirname(base_dir()), "assets", "digits", name)
        return parent if os.path.exists(parent) else local

    def set_time_text(self, text):
        self.time_label.setText(text) # Always set text for update_layout
        if self.digits_available():
            self.time_label.hide()
            self.update_layout() # This now calls show_digit_time internally
        else:
            self.digit_container.hide()
            self.time_label.show()
            self.update_layout() 

    def show_digit_time(self, text):
        if not text: text = "00:00"
        container_w = self.width()
        container_h = self.height()
        
        if text == "INF":
            p = self.digit_path("infinite") 
            pm = QtGui.QPixmap(p)
            if pm.isNull():
                 self.digit_container.hide()
                 self.time_label.setText("∞")
                 self.time_label.show()
                 return

            for lbl in self.digit_labels:
                lbl.hide()
            
            lbl = self.digit_labels[0]
            lbl.show()
            if self.flipped:
                pm = pm.transformed(QtGui.QTransform().scale(1, -1))
            lbl.setPixmap(pm)
            lbl.setScaledContents(True)
            
            aspect = pm.width() / max(1, pm.height())
            target_h = int(container_h * 0.8) # Keep some margin from background edges
            target_w = int(target_h * aspect)
            
            if target_w > container_w * 0.85:
                target_w = int(container_w * 0.85)
                target_h = int(target_w / aspect)
            
            lbl.setFixedSize(target_w, target_h)
            lbl.move((container_w - target_w) // 2, (container_h - target_h) // 2)
            
            self.digit_container.show()
            self.digit_container.raise_()
            return

        chars = [text[0], text[1], ":", text[3], text[4]]

        pixmaps = []
        for ch in chars:
            p = self.digit_path(ch)
            pm = QtGui.QPixmap(p)
            if self.flipped and not pm.isNull():
                pm = pm.transformed(QtGui.QTransform().scale(1, -1))
            pixmaps.append(pm if not pm.isNull() else QtGui.QPixmap())
        
        # Scale digits to fit within the background height with some margin
        final_height = int(container_h * 0.38) # Keep consistent with user's last setting
            
        scaled = []
        for pm in pixmaps:
            if pm.isNull():
                s_pm = QtGui.QPixmap()
            else:
                s_pm = pm.scaledToHeight(final_height, QtCore.Qt.SmoothTransformation)
            scaled.append(s_pm)
        
        # [CRITICAL] Use manual positioning to support TRUE overlap
        # Layouts don't reliably support negative spacing for transparent images.
        spacing = int(final_height * -0.1) # Start with a tight default
        
        # Calculate total width with overlap
        total_w = 0
        for i, spm in enumerate(scaled):
            w = spm.width() if not spm.isNull() else int(final_height * 0.4)
            if i == 0:
                total_w = w
            else:
                total_w += w + spacing

        # If too wide, scale down
        if total_w > container_w * 0.95:
            ratio = (container_w * 0.95) / total_w
            final_height = int(final_height * ratio)
            spacing = int(final_height * -1.1)
            # Re-scale pixmaps
            new_scaled = []
            total_w = 0.5
            for i, pm in enumerate(pixmaps):
                if pm.isNull():
                    s_pm = QtGui.QPixmap()
                    w = int(final_height * 0.4)
                else:
                    s_pm = pm.scaledToHeight(final_height, QtCore.Qt.SmoothTransformation)
                    w = s_pm.width()
                new_scaled.append(s_pm)
                if i == 0: total_w = w
                else: total_w += w + spacing
            scaled = new_scaled

        # Position digits
        left_margin = (container_w - total_w) * 0.5 # Match user's left-aligned preference
        top_margin = (container_h - final_height) * 0.5
        
        current_x = int(left_margin)
        for i, spm in enumerate(scaled):
            lbl = self.digit_labels[i]
            lbl.setPixmap(spm)
            w = spm.width() if not spm.isNull() else int(final_height * 0.4)
            lbl.setFixedSize(w, final_height)
            lbl.move(current_x, int(top_margin))
            lbl.show()
            current_x += w + spacing
            
        self.digit_container.show()
        self.digit_container.raise_()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # Shift + Drag = Global Move (forward to main window)
            if event.modifiers() & QtCore.Qt.ShiftModifier:
                if self.main_window:
                    # Pass the event to the main window to initiate its drag
                    self.main_window.mousePressEvent(event)
                event.accept()
                return

            # Ctrl + Drag = Move Timer Position
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
                                 self.main_window.set_pixmap(pix)
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
        # If main window is dragging, this widget should not also drag itself.
        if self.main_window and self.main_window.dragging:
            self.main_window.mouseMoveEvent(event)
            event.accept()
            return

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
            # Forward global drag release to main window
            if self.main_window and self.main_window.dragging:
                self.main_window.mouseReleaseEvent(event)
                event.accept()
                return

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
