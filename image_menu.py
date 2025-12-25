from PySide6 import QtCore, QtGui, QtWidgets
import os

def base_dir():
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
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
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)  # Ensure background is painted
        self.setObjectName("ContextMenu")
        
        # Check for menu background image
        menu_bg = resolve_menu_icon("menu_bg.png")
        if menu_bg and os.path.exists(menu_bg):
             # Use background image
             bg_path = menu_bg.replace('\\', '/')
             self.setStyleSheet(f"""
                #ContextMenu {{
                    border-image: url({bg_path}) 0 0 0 0 stretch stretch;
                    border: none;
                    border-radius: 8px;
                }}
            """)
        else:
            # Fallback style
            self.setStyleSheet("""
                #ContextMenu {
                    background-color: rgba(255, 255, 255, 0.95);
                    border: 1px solid #ccc;
                    border-radius: 8px;
                }
            """)

        self.setup_ui()
        self.setMinimumWidth(250)  # Make menu wider as requested

    def paintEvent(self, event):
        opt = QtWidgets.QStyleOption()
        opt.initFrom(self)
        p = QtGui.QPainter(self)
        self.style().drawPrimitive(QtWidgets.QStyle.PE_Widget, opt, p, self)

    def setup_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        # Increase vertical margins to make the menu taller ("not so flat")
        root.setContentsMargins(15, 20, 15, 20)
        root.setSpacing(10) # Increase spacing between rows

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(2) # Make top row buttons compact
        top.setAlignment(QtCore.Qt.AlignCenter) # Center the buttons
        
        bottom = QtWidgets.QHBoxLayout()
        bottom.setSpacing(6)

        self.btn_pause = QtWidgets.QPushButton("暂停", self)
        self.setup_btn(self.btn_pause, "pause.png", "暂停")
        self.btn_pause.clicked.connect(lambda: (self.owner.pause_timer(), self.close()))

        self.btn_top = QtWidgets.QPushButton("", self)
        self.btn_top.clicked.connect(lambda: (self.owner.toggle_always_on_top(), self.refresh_controls()))
        
        self.btn_exit = QtWidgets.QPushButton("退出", self)
        self.setup_btn(self.btn_exit, "exit.png", "退出")
        self.btn_exit.clicked.connect(lambda: (QtWidgets.QApplication.quit(), self.close()))

        # Interval Button (Moved to top row)
        self.btn_interval = QtWidgets.QPushButton(self.owner.voice_interval_label_text(), self)
        self.btn_interval.clicked.connect(lambda: (self.owner.cycle_voice_interval(), self.refresh_controls()))

        top.addWidget(self.btn_pause)
        top.addWidget(self.btn_top)
        top.addWidget(self.btn_interval)
        top.addWidget(self.btn_exit)
        
        # Bottom area for settings (checkbox style) -> Moved to top
        settings_layout = QtWidgets.QVBoxLayout()
        settings_layout.setSpacing(2)
        settings_layout.setAlignment(QtCore.Qt.AlignCenter)  # Center align the settings buttons
        
        self.btn_check_update = QtWidgets.QPushButton("", self)
        self.btn_check_update.clicked.connect(lambda: (self.owner.toggle_check_updates(), self.refresh_controls()))
        settings_layout.addWidget(self.btn_check_update)

        self.btn_exit_voice = QtWidgets.QPushButton("", self)
        self.btn_exit_voice.clicked.connect(lambda: (self.owner.toggle_exit_voice(), self.refresh_controls()))
        settings_layout.addWidget(self.btn_exit_voice)

        root.addLayout(settings_layout)
        root.addLayout(top)
        # root.addLayout(middle) # Removed
        # root.addLayout(settings_layout) # Moved to top

    def setup_btn(self, btn, icon_name, text):
        path = resolve_menu_icon(icon_name)
        if path and os.path.exists(path):
            btn.setText("")
            btn.setIcon(QtGui.QIcon(path))
            btn.setIconSize(QtCore.QSize(20, 20))
            btn.setFixedSize(28, 28)
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
        btn.setIconSize(QtCore.QSize(18, 18))
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
                max_height = 24
                if pix.height() > max_height:
                    pix = pix.scaledToHeight(max_height, QtCore.Qt.SmoothTransformation)
                    
                btn.setIcon(QtGui.QIcon(pix))
                btn.setIconSize(pix.size())
                # Add a little padding or match image size exactly
                btn.setFixedSize(pix.width() + 8, pix.height() + 8)
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
        # btn.setFixedSize(QtCore.QSize(16777215, 16777215)) # REMOVED: Caused layout explosion
        
        # Remove fixed size constraint
        btn.setMinimumSize(0, 0)
        btn.setMaximumSize(16777215, 16777215)
        
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
        max_height = 24
        if pix_main.height() > max_height:
             pix_main = pix_main.scaledToHeight(max_height, QtCore.Qt.SmoothTransformation)
        
        btn.setText("")
        btn.setIcon(QtGui.QIcon(pix_main))
        btn.setIconSize(pix_main.size())
        
        # Calculate size
        # We need space for the checkmark on the left.
        check_width = 20 # Reduced from 24
        padding = 4
        total_width = check_width + padding + pix_main.width() + padding
        total_height = max(pix_main.height(), 20) + padding * 2
        
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
