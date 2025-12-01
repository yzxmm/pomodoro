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
        self.btn_pause.clicked.connect(lambda: (self.owner.pause_timer(), self.hide()))

        self.btn_top = QtWidgets.QPushButton("置顶", self)
        self.btn_top.clicked.connect(lambda: (self.owner.toggle_always_on_top(), self.refresh_controls(), self.hide()))

        self.btn_exit = QtWidgets.QPushButton("退出", self)
        self.btn_exit.clicked.connect(lambda: (QtWidgets.QApplication.quit(), self.hide()))

        top.addWidget(self.btn_pause)
        top.addWidget(self.btn_top)
        top.addWidget(self.btn_exit)

        self.btn_interval = QtWidgets.QPushButton(self.owner.voice_interval_label_text(), self)
        self.btn_interval.clicked.connect(lambda: (self.owner.cycle_voice_interval(), self.refresh_controls(), self.hide()))
        bottom.addWidget(self.btn_interval)

        root.addLayout(top)
        root.addLayout(bottom)

    def show_at(self, global_pos):
        self.refresh_controls()
        self.adjustSize()
        self.move(global_pos - QtCore.QPoint(self.width() // 2, self.height() // 2))
        self.show()

    def refresh_controls(self):
        self.btn_top.setText("取消置顶" if getattr(self.owner, 'always_on_top', True) else "置顶")
        self.btn_interval.setText(self.owner.voice_interval_label_text())
