from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtUiTools import QUiLoader
import os
from utils import base_dir, asset_path
try:
    import resources_rc
except Exception:
    resources_rc = None

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
        self.ui_scale = 1.0
        self.ui_root = None
        self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlag(QtCore.Qt.NoDropShadowWindowHint, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setObjectName("ContextMenuHost")
        
        # Apply background only when not using Designer UI
        if not self.try_load_designer_ui():
            menu_bg = resolve_menu_icon("menu_bg.png")
            if menu_bg and os.path.exists(menu_bg):
                 bg_path = menu_bg.replace('\\', '/')
                 self.setStyleSheet(f"""
                    #ContextMenuHost {{
                        border-image: url({bg_path}) 0 0 0 0 stretch stretch;
                        border: none;
                        border-radius: 8px;
                    }}
                """)
            else:
                self.setStyleSheet("""
                    #ContextMenuHost {
                        background-color: rgba(255, 255, 255, 0.95);
                        border: 1px solid #ccc;
                        border-radius: 8px;
                    }
                """)
            self.setup_ui()
        self.setMinimumWidth(int(250 * self.ui_scale))

    def set_scale(self, scale):
        self.ui_scale = scale
        if self.ui_root:
            self.refresh_controls()
            self.adjustSize()
        else:
            self.setup_ui()
            self.refresh_controls()
            self.adjustSize()

    def paintEvent(self, event):
        opt = QtWidgets.QStyleOption()
        opt.initFrom(self)
        p = QtGui.QPainter(self)
        self.style().drawPrimitive(QtWidgets.QStyle.PE_Widget, opt, p, self)

    def keyPressEvent(self, event):
        # Forward key events to owner (PomodoroWidget) for cheat codes
        self.owner.keyPressEvent(event)
        super().keyPressEvent(event)
    def resolve_ui_path(self, name):
        # Use utils.resolve_path to handle Frozen/Dev environments correctly
        from utils import resolve_path
        # We assume menu.ui is at the root level in the bundle
        return resolve_path(".", name)

    def try_load_designer_ui(self):
        try:
            ui_path = self.resolve_ui_path("menu.ui")
            if not os.path.exists(ui_path):
                return False
            loader = QUiLoader()
            root_widget = loader.load(ui_path, self)
            if not root_widget:
                return False
            if self.layout():
                QtWidgets.QWidget().setLayout(self.layout())
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(root_widget)
            self.ui_root = root_widget
            
            # [Fix] Sync size from Designer to runtime
            # Prevent the window from being squashed if user uses free layout (no constraints)
            # We use the geometry from Designer as the authoritative size.
            designer_size = root_widget.geometry().size()
            if designer_size.width() > 10 and designer_size.height() > 10:
                self.setFixedSize(designer_size)
            
            # Clear host background to avoid double backgrounds
            self.setStyleSheet(" #ContextMenuHost { background: transparent; border: none; } ")
            self.bind_ui_controls()
            self.refresh_controls()
            return True
        except Exception:
            return False
    def bind_ui_controls(self):
        def find_btn(name):
            if self.ui_root:
                b = self.ui_root.findChild(QtWidgets.QPushButton, name)
                if b:
                    return b
            return None
        self.btn_pause = find_btn("btn_pause") or QtWidgets.QPushButton("暂停", self)
        self.btn_top = find_btn("btn_top") or QtWidgets.QPushButton("", self)
        self.btn_interval = find_btn("btn_interval") or QtWidgets.QPushButton("间隔", self)
        self.btn_exit = find_btn("btn_exit") or QtWidgets.QPushButton("退出", self)
        self.btn_check_update = find_btn("btn_check_update") or QtWidgets.QPushButton("", self)
        self.btn_exit_voice = find_btn("btn_exit_voice") or QtWidgets.QPushButton("", self)
        for b in (self.btn_pause, self.btn_top, self.btn_interval, self.btn_exit, self.btn_check_update, self.btn_exit_voice):
            try:
                b.setText("")
                b.setFlat(True)
            except Exception:
                pass
        self.setup_btn(self.btn_pause, "pause.png", "暂停")
        self.setup_btn(self.btn_exit, "exit.png", "退出")
        self.btn_pause.clicked.connect(lambda: (self.owner.pause_timer(), self.close()))
        self.btn_top.clicked.connect(lambda: (self.owner.toggle_always_on_top(), self.refresh_controls()))
        self.btn_interval.clicked.connect(lambda: (self.owner.toggle_interval_voice(), self.refresh_controls()))
        self.btn_exit.clicked.connect(lambda: (self.close(), self.owner.close()))
        self.btn_check_update.clicked.connect(lambda: (self.owner.toggle_check_updates(), self.refresh_controls()))
        self.btn_exit_voice.clicked.connect(lambda: (self.owner.toggle_exit_voice(), self.refresh_controls()))
    def setup_ui(self):
        # Clear existing layout
        if self.layout():
            QtWidgets.QWidget().setLayout(self.layout())

        root = QtWidgets.QVBoxLayout(self)
        # Increase vertical margins to make the menu taller ("not so flat")
        m_h = int(15 * self.ui_scale)
        m_v = int(20 * self.ui_scale)
        root.setContentsMargins(m_h, m_v, m_h, m_v)
        root.setSpacing(int(10 * self.ui_scale)) # Increase spacing between rows

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(int(2 * self.ui_scale)) # Make top row buttons compact
        top.setAlignment(QtCore.Qt.AlignCenter) # Center the buttons
        
        bottom = QtWidgets.QHBoxLayout()
        bottom.setSpacing(int(6 * self.ui_scale))

        self.btn_pause = QtWidgets.QPushButton("暂停", self)
        self.setup_btn(self.btn_pause, "pause.png", "暂停")
        self.btn_pause.clicked.connect(lambda: (self.owner.pause_timer(), self.close()))

        self.btn_top = QtWidgets.QPushButton("", self)
        self.btn_top.clicked.connect(lambda: (self.owner.toggle_always_on_top(), self.refresh_controls()))
        
        self.btn_exit = QtWidgets.QPushButton("退出", self)
        self.setup_btn(self.btn_exit, "exit.png", "退出")
        self.btn_exit.clicked.connect(lambda: (self.close(), self.owner.close()))

        self.btn_interval = QtWidgets.QPushButton("间隔", self)
        self.btn_interval.clicked.connect(lambda: (self.owner.toggle_interval_voice(), self.refresh_controls()))

        top.addWidget(self.btn_pause)
        top.addWidget(self.btn_top)
        top.addWidget(self.btn_interval)
        top.addWidget(self.btn_exit)
        
        # Bottom area for settings (checkbox style) -> Moved to top
        settings_layout = QtWidgets.QVBoxLayout()
        settings_layout.setSpacing(int(2 * self.ui_scale))
        settings_layout.setAlignment(QtCore.Qt.AlignCenter)  # Center align the settings buttons
        
        self.btn_check_update = QtWidgets.QPushButton("", self)
        self.btn_check_update.clicked.connect(lambda: (self.owner.toggle_check_updates(), self.refresh_controls()))
        settings_layout.addWidget(self.btn_check_update)

        self.btn_exit_voice = QtWidgets.QPushButton("", self)
        self.btn_exit_voice.clicked.connect(lambda: (self.owner.toggle_exit_voice(), self.refresh_controls()))
        settings_layout.addWidget(self.btn_exit_voice)

        root.addLayout(settings_layout)
        root.addLayout(top)
        
        self.setMinimumWidth(int(250 * self.ui_scale))


    def setup_btn(self, btn, icon_name, text):
        path = resolve_menu_icon(icon_name)
        if path and os.path.exists(path):
            btn.setText("")
            btn.setIcon(QtGui.QIcon(path))
            s = int(20 * self.ui_scale)
            btn.setIconSize(QtCore.QSize(s, s))
            bs = int(28 * self.ui_scale)
            btn.setFixedSize(bs, bs)
            btn.setStyleSheet("QPushButton { border: none; background: transparent; } QPushButton:hover { background: rgba(128, 128, 128, 0.2); border-radius: 4px; }")
            return True
        else:
            btn.setText(text)
            return False

    def setup_check_btn(self, btn, text, is_checked, checked_icon="check.png"):
        path = resolve_menu_icon(checked_icon)
        if is_checked and path and os.path.exists(path):
            btn.setIcon(QtGui.QIcon(path))
        else:
            btn.setIcon(QtGui.QIcon()) # No icon if unchecked or missing
            
        btn.setText(f" {text}") # Add some spacing
        s = int(18 * self.ui_scale)
        btn.setIconSize(QtCore.QSize(s, s))
        # Make it look like a menu item
        pad = int(4 * self.ui_scale)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                border: none; 
                background: transparent; 
                text-align: left;
                padding: {pad}px;
            }} 
            QPushButton:hover {{ 
                background: rgba(128, 128, 128, 0.2); 
                border-radius: 4px; 
            }}
        """)

    def setup_full_image_btn(self, btn, image_name, fallback_text):
        """
        Sets up a button to use a full image if available, otherwise text.
        Dynamic sizing based on image.
        """
        path = resolve_menu_icon(image_name)
        if path and os.path.exists(path):
            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                btn.setText("")
                
                # Scale if too large
                max_height = int(24 * self.ui_scale)
                if pix.height() > max_height:
                    pix = pix.scaledToHeight(max_height, QtCore.Qt.SmoothTransformation)
                    
                btn.setIcon(QtGui.QIcon(pix))
                btn.setIconSize(pix.size())
                # Add a little padding or match image size exactly
                pad = int(8 * self.ui_scale)
                btn.setFixedSize(pix.width() + pad, pix.height() + pad)
                btn.setStyleSheet("""
                    QPushButton { 
                        border: none; 
                        background: transparent; 
                        padding: 0px;
                    } 
                    QPushButton:hover { 
                        background: rgba(128, 128, 128, 0.2); 
                        border-radius: 4px; 
                    }
                """)
                return True
        
        # Fallback to text
        btn.setText(fallback_text)
        btn.setIcon(QtGui.QIcon())
        
        # Remove fixed size constraint
        btn.setMinimumSize(0, 0)
        btn.setMaximumSize(16777215, 16777215)
        
        pad = int(4 * self.ui_scale)
        btn.setStyleSheet(f"""
            QPushButton {{ 
                border: none; 
                background: transparent; 
                text-align: left;
                padding: {pad}px;
            }} 
            QPushButton:hover {{ 
                background: rgba(128, 128, 128, 0.2); 
                border-radius: 4px; 
            }}
        """)
        return False


    def setup_image_check_btn(self, btn, main_image_name, fallback_text, is_checked, check_icon_name="check.png"):
        """
        Sets up a button with: [CheckIcon/Blank] [MainImage]
        """
        main_path = resolve_menu_icon(main_image_name)
        check_path = resolve_menu_icon(check_icon_name)
        
        has_main = main_path and os.path.exists(main_path)
        has_check = check_path and os.path.exists(check_path)
        
        if not has_main:
             # Fallback to standard text check btn
             self.setup_check_btn(btn, fallback_text, is_checked, check_icon_name)
             return

        # We have the main image.
        pix_main = QtGui.QPixmap(main_path)
        
        # Scale main image if too large
        max_height = int(24 * self.ui_scale)
        if pix_main.height() > max_height:
             pix_main = pix_main.scaledToHeight(max_height, QtCore.Qt.SmoothTransformation)
        
        btn.setText("")
        btn.setIcon(QtGui.QIcon(pix_main))
        btn.setIconSize(pix_main.size())
        
        # Calculate size
        # We need space for the checkmark on the left.
        check_width = int(20 * self.ui_scale)
        padding = int(4 * self.ui_scale)
        total_width = check_width + padding + pix_main.width() + padding
        total_height = max(pix_main.height(), int(20 * self.ui_scale)) + padding * 2
        
        btn.setFixedSize(total_width, total_height)
        
        # Style
        # If checked, show checkmark on left.
        bg_style = ""
        if is_checked and has_check:
             # Escape path for CSS
             c_path = check_path.replace('\\', '/')
             # background: url(...) left center no-repeat;
             bg_style = f"background-image: url({c_path}); background-position: left center; background-repeat: no-repeat;"
        
        btn.setStyleSheet(f"""
            QPushButton {{ 
                border: none; 
                background-color: transparent; 
                {bg_style}
                padding-left: {check_width}px; /* Space for checkmark */
                text-align: left;
            }} 
            QPushButton:hover {{ 
                background-color: rgba(128, 128, 128, 0.2); 
                border-radius: 4px; 
            }}
        """)


    def show_at(self, global_pos):
        try:
            self.refresh_controls()
            self.adjustSize()
            self.move(global_pos - QtCore.QPoint(self.width() // 2, self.height() // 2))
            self.show()
            self.raise_()
            self.activateWindow()
            self.setFocus()
        except Exception as e:
            print(f"ERROR in show_at: {e}")

    def refresh_controls(self):
        try:
            is_top = getattr(self.owner, 'always_on_top', True)
            
            # Update top toggle button (Static Image, state implied)
            self.setup_full_image_btn(self.btn_top, "pin.png", "置顶")
            
            # Update Interval Button (Dynamic Image)
            interval = int(self.owner.voice_interval_minutes or 0)
            interval_img = f"interval_{interval}.png"
            self.setup_full_image_btn(self.btn_interval, interval_img, self.owner.voice_interval_label_text())
            
            # Update Settings Buttons
            # Exit Voice (Image + Checkmark state)
            exit_voice_on = getattr(self.owner, 'exit_voice_enabled', True)
            self.setup_image_check_btn(self.btn_exit_voice, "exit_voice.png", "结束时播放语音", exit_voice_on)
            
            # Check Updates (Image + Checkmark state)
            check_update_on = getattr(self.owner, 'check_updates_enabled', True)
            self.setup_image_check_btn(self.btn_check_update, "update.png", "检查语音更新", check_update_on)
        except Exception as e:
            print(f"ERROR in refresh_controls: {e}")
            raise
