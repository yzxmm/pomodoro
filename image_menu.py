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

        self.btn_top = QtWidgets.QPushButton("置顶", self)
        # Dynamic update in refresh_controls
        self.btn_top.clicked.connect(lambda: (self.owner.toggle_always_on_top(), self.refresh_controls(), self.close()))

        self.btn_exit = QtWidgets.QPushButton("退出", self)
        self.setup_btn(self.btn_exit, "exit.png", "退出")
        self.btn_exit.clicked.connect(lambda: (QtWidgets.QApplication.quit(), self.close()))

        top.addWidget(self.btn_pause)
        top.addWidget(self.btn_top)
        top.addWidget(self.btn_exit)

        self.btn_interval = QtWidgets.QPushButton(self.owner.voice_interval_label_text(), self)
        self.btn_interval.clicked.connect(lambda: (self.owner.cycle_voice_interval(), self.refresh_controls()))
        bottom.addWidget(self.btn_interval)

        self.btn_exit_voice = QtWidgets.QPushButton("", self)
        self.btn_exit_voice.clicked.connect(lambda: (self.owner.toggle_exit_voice(), self.refresh_controls()))
        bottom.addWidget(self.btn_exit_voice)

        root.addLayout(top)
        root.addLayout(bottom)

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

    def show_at(self, global_pos):
        self.refresh_controls()
        self.adjustSize()
        self.move(global_pos - QtCore.QPoint(self.width() // 2, self.height() // 2))
        self.show()

    def refresh_controls(self):
        is_top = getattr(self.owner, 'always_on_top', True)
        # Try to load pin/unpin icons
        icon_name = "unpin.png" if is_top else "pin.png"
        text = "取消置顶" if is_top else "置顶"
        if not self.setup_btn(self.btn_top, icon_name, text):
            self.btn_top.setText(text)
            
        self.btn_interval.setText(self.owner.voice_interval_label_text())
        
        exit_voice_on = getattr(self.owner, 'exit_voice_enabled', True)
        # State labeling: "退出语音：开启" means it IS On. "退出语音：关闭" means it IS Off.
        state_text = "开启" if exit_voice_on else "关闭"
        self.btn_exit_voice.setText(f"退出语音：{state_text}")
