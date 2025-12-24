from PySide6 import QtCore, QtGui, QtWidgets
import os

def base_dir():
    import sys
    return os.path.dirname(os.path.abspath(__file__))

def asset_path(*parts):
    return os.path.join(base_dir(), "assets", *parts)

def resolve_menu_icon(name):
    local = asset_path("menu", name)
    if os.path.exists(local):
        return local
    parent = os.path.join(os.path.dirname(base_dir()), "assets", "menu", name)
    return parent if os.path.exists(parent) else local

class ImageMenu(QtWidgets.QFrame):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        bottom = QtWidgets.QHBoxLayout()
        bottom.setSpacing(8)

        self.btn_pause = QtWidgets.QPushButton("暂停", self)
        self.setup_btn(self.btn_pause, "pause.png", "暂停")
        self.btn_pause.clicked.connect(lambda: (self.owner.pause_timer(), self.close()))

        # Old button removed to avoid duplication
        # self.btn_top = QtWidgets.QPushButton("置顶", self)
        
        self.btn_exit = QtWidgets.QPushButton("退出", self)
        self.setup_btn(self.btn_exit, "exit.png", "退出")
        self.btn_exit.clicked.connect(lambda: (QtWidgets.QApplication.quit(), self.close()))

        top.addWidget(self.btn_pause)
        top.addWidget(self.btn_exit)

        # Middle row for Interval
        middle = QtWidgets.QHBoxLayout()
        self.btn_interval = QtWidgets.QPushButton(self.owner.voice_interval_label_text(), self)
        self.btn_interval.clicked.connect(lambda: (self.owner.cycle_voice_interval(), self.refresh_controls()))
        middle.addWidget(self.btn_interval)
        
        # Bottom area for settings (checkbox style)
        settings_layout = QtWidgets.QVBoxLayout()
        settings_layout.setSpacing(2)
        
        self.btn_top_text = QtWidgets.QPushButton("", self)
        self.btn_top_text.clicked.connect(lambda: (self.owner.toggle_always_on_top(), self.refresh_controls()))
        settings_layout.addWidget(self.btn_top_text)

        self.btn_exit_voice = QtWidgets.QPushButton("", self)
        self.btn_exit_voice.clicked.connect(lambda: (self.owner.toggle_exit_voice(), self.refresh_controls()))
        settings_layout.addWidget(self.btn_exit_voice)

        self.btn_check_update = QtWidgets.QPushButton("", self)
        self.btn_check_update.clicked.connect(lambda: (self.owner.toggle_check_updates(), self.refresh_controls()))
        settings_layout.addWidget(self.btn_check_update)

        root.addLayout(top)
        root.addLayout(middle)
        root.addLayout(settings_layout)

    def setup_btn(self, btn, icon_name, text):
        path = resolve_menu_icon(icon_name)
        if path and os.path.exists(path):
            btn.setText("")
            btn.setIcon(QtGui.QIcon(path))
            btn.setIconSize(QtCore.QSize(24, 24))
            btn.setFixedSize(32, 32)
            btn.setStyleSheet("QPushButton { border: none; background: transparent; } QPushButton:hover { background: rgba(128, 128, 128, 0.2); border-radius: 4px; }")
            return True
        else:
            btn.setText(text)
            return False

    def setup_check_btn(self, btn, text, is_checked):
        # Layout for checkbox-style button: [Icon] Text
        # But QPushButton icon is usually on the left.
        # We want to use a custom icon for "checked" state (hand-drawn tick)
        
        path = resolve_menu_icon("check.png")
        if is_checked and path and os.path.exists(path):
            btn.setIcon(QtGui.QIcon(path))
        else:
            btn.setIcon(QtGui.QIcon()) # No icon if unchecked or missing
            
        btn.setText(f" {text}") # Add some spacing
        btn.setIconSize(QtCore.QSize(20, 20))
        # Make it look like a menu item
        btn.setStyleSheet("""
            QPushButton { 
                border: none; 
                background: transparent; 
                text-align: left;
                padding: 4px;
            } 
            QPushButton:hover { 
                background: rgba(128, 128, 128, 0.2); 
                border-radius: 4px; 
            }
        """)

    def show_at(self, global_pos):
        self.refresh_controls()
        self.adjustSize()
        self.move(global_pos - QtCore.QPoint(self.width() // 2, self.height() // 2))
        self.show()

    def refresh_controls(self):
        is_top = getattr(self.owner, 'always_on_top', True)
        # Update top toggle button (icon based) - REMOVED from top row
        # icon_name = "unpin.png" if is_top else "pin.png"
        # text = "取消置顶" if is_top else "置顶"
        # if not self.setup_btn(self.btn_top, icon_name, text):
        #     self.btn_top.setText(text)
            
        # Update top toggle button (checkbox style)
        self.setup_check_btn(self.btn_top_text, "置顶", is_top)
            
        self.btn_interval.setText(self.owner.voice_interval_label_text())
        
        exit_voice_on = getattr(self.owner, 'exit_voice_enabled', True)
        # Update exit voice toggle (checkbox style)
        self.setup_check_btn(self.btn_exit_voice, "启用退出语音", exit_voice_on)
        
        check_update_on = getattr(self.owner, 'check_updates_enabled', True)
        self.setup_check_btn(self.btn_check_update, "检查语音更新", check_update_on)
