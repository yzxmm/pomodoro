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
        self._original_stylesheets = {} # Cache for Designer UI styles
        self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlag(QtCore.Qt.NoDropShadowWindowHint, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setObjectName("ContextMenuHost")
        
        self.bg_pixmap = QtGui.QPixmap()
        self.bg_aspect_ratio = 1.0

        # Apply background only when not using Designer UI
        if not self.try_load_designer_ui():
            menu_bg = resolve_menu_icon("menu_bg.png")
            if menu_bg and os.path.exists(menu_bg):
                 self.bg_pixmap = QtGui.QPixmap(menu_bg)
                 if not self.bg_pixmap.isNull():
                     self.bg_aspect_ratio = self.bg_pixmap.width() / max(1, self.bg_pixmap.height())
                 
                 self.setStyleSheet("""
                    #ContextMenuHost {
                        background: transparent;
                        border: none;
                    }
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
        # [Performance] Debounce menu scaling. Rebuilding UI is expensive.
        if abs(self.ui_scale - scale) < 0.05:
            return
            
        self.ui_scale = scale
        if self.ui_root:
            self.refresh_controls()
            self.adjustSize()
        else:
            self.setup_ui()
            self.refresh_controls()
            self.adjustSize()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        if not self.bg_pixmap.isNull():
            # [CRITICAL FIX] Draw background maintaining aspect ratio exactly
            # We use SmoothTransformation for the highest quality.
            target_rect = self.rect()
            painter.drawPixmap(target_rect, self.bg_pixmap)
        else:
            opt = QtWidgets.QStyleOption()
            opt.initFrom(self)
            self.style().drawPrimitive(QtWidgets.QStyle.PE_Widget, opt, painter, self)

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
            # We use the geometry from Designer as the authoritative size, scaled.
            designer_size = root_widget.geometry().size()
            if designer_size.width() > 10 and designer_size.height() > 10:
                scaled_size = QtCore.QSize(
                    int(designer_size.width() * self.ui_scale),
                    int(designer_size.height() * self.ui_scale)
                )
                self.setFixedSize(scaled_size)
                # Also scale the inner widget to fill the host
                root_widget.setFixedSize(scaled_size)
                
                # [Fix] Scale icon sizes for all buttons if scale is not 1.0
                if abs(self.ui_scale - 1.0) > 0.01:
                    for btn in root_widget.findChildren(QtWidgets.QPushButton):
                        sz = btn.iconSize()
                        if not sz.isEmpty():
                            btn.setIconSize(sz * self.ui_scale)
            
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
        
        # Store original stylesheets from Designer UI for state-based updates
        if self.ui_root:
            for b in (self.btn_pause, self.btn_top, self.btn_interval, self.btn_exit, self.btn_check_update, self.btn_exit_voice):
                if b and b.objectName():
                    self._original_stylesheets[b.objectName()] = b.styleSheet()

        # Connect signals and ensure functional defaults
        for b in (self.btn_pause, self.btn_top, self.btn_interval, self.btn_exit, self.btn_check_update, self.btn_exit_voice):
            try:
                # Set buttons to flat mode to avoid system default hover backgrounds
                b.setFlat(True)
                # If not using Designer UI, apply default flattening and clear text
                if not self.ui_root:
                    b.setText("")
            except Exception:
                pass
        
        # Initial icons (will be updated by refresh_controls for stateful buttons)
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
            # Only set default sizes if we are NOT using the Designer UI root
            if not self.ui_root:
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
        if not self.ui_root:
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
        else:
            # For Designer UI, we can still ensure it behaves like a flat menu item
            # But we should be careful not to override everything.
            # We'll rely on setup_image_check_btn's stylesheet injection if called from there.
            pass

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
                
                # Only scale and style if NOT using Designer UI root
                if not self.ui_root:
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
                else:
                    # In Designer mode, just set the icon.
                    # We assume the user has set an appropriate iconSize in Designer.
                    btn.setIcon(QtGui.QIcon(pix))
                return True
        
        # Fallback to text
        btn.setText(fallback_text)
        btn.setIcon(QtGui.QIcon())
        
        # Remove fixed size constraint
        if not self.ui_root:
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
        
        # Scale main image if too large (only in manual mode)
        if not self.ui_root:
            max_height = int(24 * self.ui_scale)
            if pix_main.height() > max_height:
                pix_main = pix_main.scaledToHeight(max_height, QtCore.Qt.SmoothTransformation)
            btn.setIconSize(pix_main.size())
        
        btn.setText("")
        btn.setIcon(QtGui.QIcon(pix_main))
        # btn.setIconSize() is intentionally skipped in Designer mode to respect the UI file's settings
        
        # Calculate size and set styles
        if not self.ui_root:
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
        else:
            # In Designer mode, we want to respect the existing layout/size
            # But we still need to show the checkmark.
            check_width = int(24 * self.ui_scale) # Standard check width
            bg_style = ""
            if is_checked and has_check:
                c_path = check_path.replace('\\', '/')
                bg_style = f"background-image: url({c_path}); background-position: left center; background-repeat: no-repeat; padding-left: {check_width}px;"
            else:
                bg_style = f"background-image: none; padding-left: {check_width}px;"
            
            # Instead of replacing the entire stylesheet, we try to just set the relevant properties
            # We use the cached original stylesheet as the base to avoid accumulation.
            existing = self._original_stylesheets.get(btn.objectName(), "")
            if not existing:
                btn.setStyleSheet(f"""
                    QPushButton {{ 
                        {bg_style}
                        text-align: left;
                        border: none;
                        background-color: transparent;
                    }} 
                """)
            else:
                # Inject checkmark style into the base stylesheet
                # Append to the end so it overrides previous rules (CSS cascade)
                # Target by object name for specificity
                obj_name = btn.objectName()
                btn.setStyleSheet(existing + f"\nQPushButton#{obj_name} {{ {bg_style} }}")


    def show_at(self, global_pos):
        try:
            self.refresh_controls()
            self.adjustSize()
            
            # [CRITICAL FIX] Ensure window matches background aspect ratio perfectly
            # This prevents any stretching of the menu_bg.png asset.
            if not self.bg_pixmap.isNull():
                # Get the size required by the layout
                req_w = self.width()
                req_h = self.height()
                
                # Calculate new size that maintains aspect ratio and covers the required area
                # We use the provided asset's own ratio as the master.
                if req_w / max(1, req_h) > self.bg_aspect_ratio:
                    # Content is wider than the background's natural shape -> Expand height
                    final_w = req_w
                    final_h = int(req_w / self.bg_aspect_ratio)
                else:
                    # Content is taller than the background's natural shape -> Expand width
                    final_h = req_h
                    final_w = int(req_h * self.bg_aspect_ratio)
                
                self.setFixedSize(final_w, final_h)
            
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
