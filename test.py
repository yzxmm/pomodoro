import os
import sys
import time
import urllib.request
import json
import threading
import random
from PySide6 import QtCore, QtGui, QtWidgets
from image_menu import ImageMenu
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


def base_dir():
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
        self.image_label.setScaledContents(False)

        pix = QtGui.QPixmap(resolve_asset("idle.png"))
        if not pix.isNull():
            self.image_label.setPixmap(pix)
            self.resize(pix.size())
        else:
            self.resize(400, 400)

        self.image_label.setGeometry(0, 0, self.width(), self.height())

        self.time_label = QtWidgets.QLabel(self)
        self.time_label.setText("00:00")
        self.time_label.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(22)
        font.setBold(True)
        self.time_label.setFont(font)
        self.time_label.setStyleSheet("color: black;")
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

        self.time_label.installEventFilter(self)

        self.dragging = False
        self.drag_offset = QtCore.QPoint()
        # digit image container for hand-written PNG digits (optional)
        self.digit_container = QtWidgets.QWidget(self)
        self.digit_container.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.digit_layout = QtWidgets.QHBoxLayout(self.digit_container)
        self.digit_layout.setContentsMargins(0, 0, 0, 0)
        self.digit_layout.setSpacing(0)
        self.digit_labels = [QtWidgets.QLabel(self.digit_container) for _ in range(5)]
        for lbl in self.digit_labels:
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setScaledContents(False)
            self.digit_layout.addWidget(lbl)
        self.digit_container.hide()

        # 确保初始几何同步
        self.place_time_label()

        self.set_time_text(self.format_time(self.work_duration))
        self.menu_overlay = ImageMenu(self)

        self.resume_button = QtWidgets.QLabel(self)
        self.resume_button.setFixedSize(100, 100)
        self.resume_button.setAlignment(QtCore.Qt.AlignCenter)
        self.resume_button.setScaledContents(True)
        rpix = QtGui.QPixmap(resolve_asset("resume.png"))
        if not rpix.isNull():
            self.resume_button.setPixmap(rpix)
        else:
            self.resume_button.setText("继续")
            self.resume_button.setStyleSheet("background: rgba(0,0,0,0.3); color: white; padding:6px; border-radius:6px;")
        self.resume_button.hide()
        self.resume_button.mousePressEvent = lambda e: (self.start_or_resume(), e.accept())
        self.resume_offset_y_ratio = 0.08

        self.start_button = QtWidgets.QPushButton("开始", self)
        self.start_button.setFixedSize(88, 34)
        self.start_button.clicked.connect(self.start_or_resume)
        self.start_button.show()
        self.place_start_button()

    def place_time_label(self):
        w = self.width()
        h = self.height()
        label_w = int(w * 0.39)
        label_h = int(h * 0.11)
        cx = int(w / 2 - w * 0.01)
        x = int(cx - label_w / 2)
        y = int(h * 0.61)
        # 手写数字PNG的显示区域，和原文字大小一致，便于调整位置
        # 位置：相对图片宽高，X=居中，Y=约图片高度的60%
        self.time_label.setGeometry(x, y, label_w, label_h)
        if hasattr(self, 'digit_container') and self.digit_container is not None:
            self.digit_container.setGeometry(x, y, label_w, label_h)

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
        bw = self.start_button.width()
        bh = self.start_button.height()
        margin = max(6, int(min(w, h) * 0.015))
        rx = max(0, w - bw - margin)
        ry = margin
        self.start_button.setGeometry(rx, ry, bw, bh)

    def resizeEvent(self, event):
        self.image_label.setGeometry(0, 0, self.width(), self.height())
        self.place_time_label()
        self.place_resume_button()
        self.place_start_button()
        super().resizeEvent(event)

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
            self.time_label.setText("")
            self.show_digit_time(text)
        else:
            self.digit_container.hide()
            self.time_label.setText(text)

    def show_digit_time(self, text):
        chars = [text[0], text[1], ":", text[3], text[4]]
        pixmaps = []
        for ch in chars:
            p = self.digit_path(ch)
            pm = QtGui.QPixmap(p)
            pixmaps.append(pm if not pm.isNull() else QtGui.QPixmap())
        height = max(1, self.digit_container.height())
        scaled = []
        for pm in pixmaps:
            if pm.isNull():
                scaled.append(QtGui.QPixmap())
            else:
                scaled.append(pm.scaledToHeight(height, QtCore.Qt.SmoothTransformation))
        for i, spm in enumerate(scaled):
            self.digit_labels[i].setPixmap(spm)
        natural_widths = [spm.width() if not spm.isNull() else 1 for spm in scaled]
        total_w = max(1, self.digit_container.width())
        pad_px = max(2, int(height * 0.06))
        pads = [pad_px, pad_px, max(1, int(pad_px * 0.6)), pad_px, pad_px]
        total_natural = sum(natural_widths[i] + pads[i] for i in range(5))
        ratio = min(1.0, total_w / total_natural) * 0.98
        for i, lbl in enumerate(self.digit_labels):
            lbl.setFixedHeight(height)
            w_i = int((natural_widths[i] + pads[i]) * ratio)
            if i == 2:
                w_i = max(w_i, max(8, int(height * 0.12)))
            lbl.setFixedWidth(max(1, w_i))
        self.digit_container.show()

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
            self.play_category('resume', default_file='start.mp3')
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
        self.maybe_ten_minute_voice()
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
            self.play_sound("start.mp3")
            self.apply_phase_visuals()

    def apply_phase_visuals(self):
        if self.paused:
            pix = QtGui.QPixmap(resolve_asset("paused.png"))
        elif self.phase == "rest":
            pix = QtGui.QPixmap(resolve_asset("paused.png"))
        elif self.phase == "working":
            pix = QtGui.QPixmap(resolve_asset("idle.png"))
        else:
            pix = QtGui.QPixmap(resolve_asset("idle.png"))
        if not pix.isNull():
            self.image_label.setPixmap(pix)
            self.resize(pix.size())
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
        if obj is self.time_label:
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
                        self.resize(pix.size())
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
                        self.resize(pix.size())
                return True
            if event.type() == QtCore.QEvent.MouseButtonRelease and self.adjusting_duration:
                self.adjusting_duration = False
                if self.phase == "idle":
                    target = self.work_duration if (self.adjust_mode == 'work') else self.rest_duration
                    self.set_time_text(self.format_time(target))
                else:
                    self.set_time_text(self.format_time(self.elapsed))
                self.adjust_mode = None
                self.apply_phase_visuals()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if not self.adjusting_duration:
                self.dragging = True
                self.drag_offset = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self.drag_offset)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.dragging = False
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

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        self.menu_overlay.show_at(event.globalPos())

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, self.always_on_top)
        self.show()

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
            'ten': self.pool_ten,
            'resume': self.pool_resume,
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
        self.pool_ten = []
        self.pool_resume = []
        self.random_pool = []
        self.seasonal_pools = {'start': {}, 'end': {}, 'ten': {}, 'resume': {}}
        self.tag_pools = {'start': {}, 'end': {}, 'ten': {}, 'resume': {}}
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
            add_dir_to(self.pool_ten, os.path.join(root, 'random', 'ten'))
            add_dir_to(self.pool_resume, os.path.join(root, 'random', 'resume'))
            for cat in ('start', 'end', 'ten', 'resume'):
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
        add_dir_to(self.pool_ten, os.path.join(cloud_root, 'ten'))
        add_dir_to(self.pool_resume, os.path.join(cloud_root, 'resume'))
        for cat in ('start', 'end', 'ten', 'resume'):
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
                manifest_url = base_url.rstrip('/') + '/manifest.json'
                with urllib.request.urlopen(manifest_url, timeout=10) as resp:
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
                        urllib.request.urlretrieve(url, dest)
                self.build_sound_pool()
            except Exception:
                pass
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

    def toggle_ten_voice(self):
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

    def voice_interval_label_text(self):
        m = int(self.voice_interval_minutes or 0)
        if m == 0:
            return "不额外播放语音"
        return f"每{m}分钟播放语音"

    # 每10分钟随机语音（分类池优先，空则兜底池）
    def maybe_ten_minute_voice(self):
        interval = int(self.voice_interval_minutes or 0)
        if interval > 0 and self.phase == 'working' and self.elapsed > 0 and self.elapsed % (interval * 60) == 0:
            if self.pool_ten:
                self.play_category('ten')
            else:
                self.play_random_voice()


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = PomodoroWidget()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
