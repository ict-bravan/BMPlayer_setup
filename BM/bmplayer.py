import sys
import os
import sqlite3
import yt_dlp
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QFileDialog, QListWidget, QSplitter, 
    QMenuBar, QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem, QDialog, QRadioButton, QButtonGroup, QScrollArea
)
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtCore import Qt, QUrl, QEvent
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

BMPLAYER_STYLE = """
QMainWindow { background: #0f172a; }
QMenuBar { background-color: #1e293b; color: #f8fafc; font-size: 13px; border-bottom: 1px solid #334155; }
QMenuBar::item { background: transparent; padding: 6px 12px; }
QMenuBar::item:selected { background: #3b82f6; border-radius: 4px; }
QMenu { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; }
QMenu::item:selected { background-color: #3b82f6; }
QPushButton { background-color: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 13px; }
QPushButton:hover { background-color: #2563eb; }
QPushButton#yt_btn { background-color: #ef4444; font-size: 14px; border-radius: 6px; }
QPushButton#yt_btn:hover { background-color: #dc2626; }
QPushButton#download_btn { background-color: #10b981; font-size: 14px; border-radius: 6px; }
QPushButton#download_btn:hover { background-color: #059669; }
QPushButton#control_btn { background-color: #334155; border-radius: 20px; min-width: 40px; min-height: 40px; font-size: 16px; }
QPushButton#control_btn:hover { background-color: #0284c7; }
QListWidget { background-color: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 8px; padding: 8px; font-size: 13px; }
QListWidget::item:selected { background-color: #3b82f6; color: white; border-radius: 4px; }
QLabel { color: #cbd5e1; font-size: 13px; }
QRadioButton { color: #f8fafc; font-size: 13px; spacing: 8px; padding: 4px; }
QRadioButton::indicator { width: 16px; height: 16px; }
QSlider::groove:horizontal { border: 1px solid #475569; height: 6px; background: #1e293b; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #3b82f6; border-radius: 3px; }
QSlider::handle:horizontal { background: #f8fafc; border: 1px solid #cbd5e1; width: 14px; margin: -4px 0; border-radius: 7px; }
QTableWidget { background-color: #020617; color: #f8fafc; border: 1px solid #334155; gridline-color: #334155; }
QHeaderView::section { background-color: #1e293b; color: white; padding: 5px; border: 1px solid #334155; }
"""

class CustomVideoWidget(QVideoWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

    def mouseDoubleClickEvent(self, event):
        if self.parent_window:
            self.parent_window.toggle_fullscreen()
        super().mouseDoubleClickEvent(event)


class VidMateStyleDownloadDialog(QDialog):
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BMPlayer - Download Hub (VidMate Style)")
        self.setGeometry(200, 120, 750, 580)
        self.setStyleSheet("background-color: #0f172a; color: white;")
        self.url = url
        self.selected_format_id = None
        self.selected_audio_preset = None
        self.selected_type = None
        
        layout = QVBoxLayout(self)
        self.title_label = QLabel("📥 Inachambua taarifa kutoka YouTube, tafadhali subiri...")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8; margin-bottom: 5px;")
        layout.addWidget(self.title_label)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #334155; background: #020617; border-radius: 6px; } QTabBar::tab { background: #1e293b; color: white; padding: 10px 20px; font-weight: bold; font-size: 13px; } QTabBar::tab:selected { background: #3b82f6; }")
        
        v_widget = QWidget()
        self.v_layout = QVBoxLayout(v_widget)
        self.video_button_group = QButtonGroup(self)
        
        v_scroll = QScrollArea()
        v_scroll.setWidgetResizable(True)
        v_scroll.setWidget(v_widget)
        v_scroll.setStyleSheet("border: none; background: transparent;")
        
        a_widget = QWidget()
        self.a_layout = QVBoxLayout(a_widget)
        self.audio_button_group = QButtonGroup(self)
        
        a_scroll = QScrollArea()
        a_scroll.setWidgetResizable(True)
        a_scroll.setWidget(a_widget)
        a_scroll.setStyleSheet("border: none; background: transparent;")
        
        self.tabs.addTab(v_scroll, "Video (MP4)")
        self.tabs.addTab(a_scroll, "Audio (MP3 / M4A)")
        layout.addWidget(self.tabs)
        
        self.btn_download = QPushButton("🚀 Anza Kupakua Sasa (High-Speed)")
        self.btn_download.setStyleSheet("background-color: #10b981; font-weight: bold; padding: 12px; font-size: 14px; border-radius: 6px;")
        self.btn_download.clicked.connect(self.confirm_selection)
        layout.addWidget(self.btn_download)
        
        self.video_radio_mapping = {}
        self.audio_radio_mapping = {}
        self.fetch_media_options()

    def fetch_media_options(self):
        try:
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                video_title = info.get('title', 'Video ya YouTube')
                self.title_label.setText(f"📌 Jina: {video_title}")
                
                formats = info.get('formats', [])
                seen_res = set()
                for f in formats:
                    if f.get('vcodec') != 'none' and f.get('ext') == 'mp4':
                        height = f.get('height')
                        if height:
                            res_label = f"{height}p"
                            if height >= 720 and height < 1440: res_label = f"{height}HD"
                            elif height >= 1440 and height < 2160: res_label = "2K HD"
                            elif height >= 2160: res_label = "4K HD"
                            
                            if res_label not in seen_res:
                                seen_res.add(res_label)
                                filesize = f.get('filesize') or f.get('filesize_approx')
                                size_str = f"{round(filesize / (1024*1024), 1)} MB" if filesize else "Size Inakadiriwa"
                                
                                radio_text = f"🎥 Video MP4 - {res_label} | Ukubwa: {size_str}"
                                rb = QRadioButton(radio_text)
                                self.video_button_group.addButton(rb)
                                self.v_layout.addWidget(rb)
                                if len(self.video_radio_mapping) == 0:
                                    rb.setChecked(True)
                                self.video_radio_mapping[rb] = f.get('format_id')

                self.v_layout.addStretch()

                audio_presets = [
                    {'name': '128k (M4A) - Ubora Mzuri', 'abr': 128, 'ext': 'm4a'},
                    {'name': '128k (MP3) - Standard MP3', 'abr': 128, 'ext': 'mp3'},
                    {'name': '256k (MP3) - Ubora wa Juu (High Quality)', 'abr': 256, 'ext': 'mp3'}
                ]
                matching_f = next((f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none'), None)
                filesize = matching_f.get('filesize') or matching_f.get('filesize_approx') if matching_f else None
                size_str = f"{round(filesize / (1024*1024), 1)} MB" if filesize else "~3-6 MB"

                for preset in audio_presets:
                    radio_text = f"🎵 Audio {preset['name']} | Ukubwa: {size_str}"
                    rb = QRadioButton(radio_text)
                    self.audio_button_group.addButton(rb)
                    self.a_layout.addWidget(rb)
                    if len(self.audio_radio_mapping) == 0:
                        rb.setChecked(True)
                    self.audio_radio_mapping[rb] = preset

                self.a_layout.addStretch()
        except Exception as e:
            self.title_label.setText(f"Hitilafu katika kupata taarifa: {str(e)}")

    def confirm_selection(self):
        current_tab = self.tabs.currentIndex()
        if current_tab == 0:
            checked_btn = self.video_button_group.checkedButton()
            if checked_btn and checked_btn in self.video_radio_mapping:
                self.selected_format_id = self.video_radio_mapping[checked_btn]
                self.selected_type = 'video'
                self.accept()
            else:
                QMessageBox.warning(self, "Onyo", "Tafadhali chagua ubora wa video kwanza.")
        else:
            checked_btn = self.audio_button_group.checkedButton()
            if checked_btn and checked_btn in self.audio_radio_mapping:
                self.selected_audio_preset = self.audio_radio_mapping[checked_btn]
                self.selected_type = 'audio'
                self.accept()
            else:
                QMessageBox.warning(self, "Onyo", "Tafadhali chagua ubora wa audio kwanza.")


class BMPlayerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BMPlayer Pro - Ultimate Fast Media & Web Suite")
        self.setGeometry(70, 50, 1350, 820)
        self.init_database()
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        self.create_menu_bar()
        QApplication.instance().installEventFilter(self)
        
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QHBoxLayout(self.main_widget)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.splitter)
        
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.logo_label = QLabel("🎬 BMPLAYER STUDIO")
        self.logo_label.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        self.left_layout.addWidget(self.logo_label)
        
        self.btn_youtube_browser = QPushButton("🔴 YouTube (Video za Moja kwa Moja)")
        self.btn_youtube_browser.setObjectName("yt_btn")
        self.btn_youtube_browser.clicked.connect(self.open_youtube_browser)
        self.left_layout.addWidget(self.btn_youtube_browser)
        
        self.btn_open = QPushButton("📂 Fungua Faili za Ndani")
        self.btn_open.clicked.connect(self.open_files)
        self.left_layout.addWidget(self.btn_open)
        
        self.playlist_widget = QListWidget()
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected_item)
        self.left_layout.addWidget(self.playlist_widget)
        self.splitter.addWidget(self.left_panel)
        
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        
        self.right_tabs = QTabWidget()
        self.right_tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #334155; background: #020617; border-radius: 8px; } QTabBar::tab { background: #1e293b; color: white; padding: 8px 15px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: bold; } QTabBar::tab:selected { background: #3b82f6; }")
        
        self.media_tab_widget = QWidget()
        media_tab_layout = QVBoxLayout(self.media_tab_widget)
        self.video_widget = CustomVideoWidget(self)
        self.video_widget.setStyleSheet("background-color: #020617; border-radius: 8px;")
        media_tab_layout.addWidget(self.video_widget)
        self.player.setVideoOutput(self.video_widget)
        
        self.info_viewer = QLabel("Karibu kwenye BMPlayer Pro\n👉 Bonyeza YouTube hapo kushoto kuona video za moja kwa moja.\n👉 Tumia Spacebar ku-Play/Pause.")
        self.info_viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_viewer.setStyleSheet("background-color: #020617; color: #38bdf8; font-size: 15px; font-weight: bold; border-radius: 8px;")
        media_tab_layout.addWidget(self.info_viewer)
        self.info_viewer.hide()
        self.right_tabs.addTab(self.media_tab_widget, "▶ Media Player")
        
        self.youtube_browser_tab = QWidget()
        yt_browser_layout = QVBoxLayout(self.youtube_browser_tab)
        yt_top_bar = QHBoxLayout()
        self.btn_yt_back = QPushButton("⬅ Rudi Nyuma")
        self.btn_yt_forward = QPushButton("Mbele ➡")
        self.btn_fast_download = QPushButton("⚡ Download Hub (Video & Audio)")
        self.btn_fast_download.setObjectName("download_btn")
        
        for btn in [self.btn_yt_back, self.btn_yt_forward]:
            btn.setStyleSheet("background-color: #334155; padding: 6px 12px;")
            yt_top_bar.addWidget(btn)
        yt_top_bar.addStretch()
        yt_top_bar.addWidget(self.btn_fast_download)
        yt_browser_layout.addLayout(yt_top_bar)
        
        self.web_engine = QWebEngineView()
        yt_browser_layout.addWidget(self.web_engine)
        self.btn_yt_back.clicked.connect(self.web_engine.back)
        self.btn_yt_forward.clicked.connect(self.web_engine.forward)
        self.btn_fast_download.clicked.connect(self.open_vidmate_download_hub)
        self.right_tabs.addTab(self.youtube_browser_tab, "🌐 YouTube Browser")
        
        self.log_tab_widget = QWidget()
        log_layout = QVBoxLayout(self.log_tab_widget)
        self.log_table = QTableWidget()
        log_layout.addWidget(QLabel("📊 Mwenendo na Kumbukumbu za Shughuli za Programu (Activity Logs):"))
        log_layout.addWidget(self.log_table)
        self.load_activity_logs()
        self.right_tabs.addTab(self.log_tab_widget, "📈 Mwenendo wa Programu (Logs)")
        self.right_layout.addWidget(self.right_tabs)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.set_position)
        self.right_layout.addWidget(self.slider)
        
        self.controls_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("control_btn")
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setObjectName("control_btn")
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setObjectName("control_btn")
        self.btn_full = QPushButton("⛶")
        self.btn_full.setObjectName("control_btn")
        
        for btn in [self.btn_play, self.btn_pause, self.btn_stop, self.btn_full]:
            self.controls_layout.addWidget(btn)
            
        self.btn_play.clicked.connect(self.player.play)
        self.btn_pause.clicked.connect(self.player.pause)
        self.btn_stop.clicked.connect(self.stop_media)
        self.btn_full.clicked.connect(self.toggle_fullscreen)
        self.controls_layout.addStretch()
        
        self.vol_label = QLabel("Sauti:")
        self.controls_layout.addWidget(self.vol_label)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.audio_output.setVolume(0.7)
        self.volume_slider.sliderMoved.connect(self.set_volume)
        self.controls_layout.addWidget(self.volume_slider)
        
        self.right_layout.addLayout(self.controls_layout)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([320, 1030])
        
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.file_paths = []
        self.open_youtube_browser()

    def init_database(self):
        try:
            self.db_conn = sqlite3.connect(":memory:")
            self.db_cursor = self.db_conn.cursor()
            self.db_cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT,
                    description TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.db_conn.commit()
        except Exception:
            pass

    def log_activity(self, action_type, description):
        try:
            self.db_cursor.execute("INSERT INTO activity_logs (action_type, description) VALUES (?, ?)", (action_type, description))
            self.db_conn.commit()
            self.load_activity_logs()
        except Exception:
            pass

    def load_activity_logs(self):
        try:
            self.db_cursor.execute("SELECT id, action_type, description, timestamp FROM activity_logs ORDER BY id DESC")
            rows = self.db_cursor.fetchall()
            self.log_table.setRowCount(len(rows))
            self.log_table.setColumnCount(4)
            self.log_table.setHorizontalHeaderLabels(["ID", "Aina ya Shughuli", "Maelezo Kamili", "Wakati (Time)"])
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    self.log_table.setItem(i, j, QTableWidgetItem(str(val)))
        except Exception:
            pass

    def create_menu_bar(self):
        menubar = self.menuBar()
        media_menu = menubar.addMenu("Media")
        media_menu.addAction(QAction("Open File...", self, triggered=self.open_files))
        media_menu.addAction(QAction("Open YouTube Browser...", self, triggered=self.open_youtube_browser))
        media_menu.addSeparator()
        media_menu.addAction(QAction("Exit", self, triggered=self.close))
        
        playback_menu = menubar.addMenu("Playback")
        playback_menu.addAction(QAction("Play / Pause (Spacebar)", self, triggered=self.toggle_play_pause))
        playback_menu.addAction(QAction("Stop", self, triggered=self.stop_media))
        
        audio_menu = menubar.addMenu("Audio")
        audio_menu.addAction(QAction("Increase Volume (Up Arrow)", self, triggered=lambda: self.adjust_volume(10)))
        audio_menu.addAction(QAction("Decrease Volume (Down Arrow)", self, triggered=lambda: self.adjust_volume(-10)))
        
        video_menu = menubar.addMenu("Video")
        video_menu.addAction(QAction("Full Screen (Double-Click / F)", self, triggered=self.toggle_fullscreen))
        
        menubar.addMenu("Subtitle")
        menubar.addMenu("Tools")
        menubar.addMenu("View")
        menubar.addMenu("Help")

    def open_youtube_browser(self):
        self.right_tabs.setCurrentIndex(1)
        self.web_engine.setUrl(QUrl("https://www.youtube.com"))
        self.log_activity("WEB_BROWSER", "Imefungua YouTube Homepage")

    def open_vidmate_download_hub(self):
        current_url = self.web_engine.url().toString()
        if "youtube.com/watch" not in current_url:
            QMessageBox.warning(self, "Onyo", "Tafadhali fungua video halisi kwanza kwenye YouTube hapo juu ndipo ubonyeze Download Hub.")
            return
            
        dialog = VidMateStyleDownloadDialog(current_url, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            save_path = QFileDialog.getExistingDirectory(self, "Chagua Folda ya Kuhifadhi Download")
            if not save_path: return
            
            QMessageBox.information(self, "Inapakua", "Upakuaji umeanzishwa kwa kasi ya juu (High-Speed)...")
            self.log_activity("DOWNLOAD_START", f"Imeanza download: {current_url}")
            
            try:
                ydl_opts = {
                    'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
                    'concurrent_fragment_downloads': 15,
                }
                if dialog.selected_type == 'video':
                    fmt_id = dialog.selected_format_id
                    ydl_opts['format'] = f"{fmt_id}+bestaudio/best"
                else:
                    preset = dialog.selected_audio_preset
                    ydl_opts['format'] = 'bestaudio/best'
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': preset['ext'],
                        'preferredquality': str(preset['abr']),
                    }]
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([current_url])
                QMessageBox.information(self, "Imefanikiwa", f"Upakuaji umekamilika kikamilifu!\nFaili limehifadhiwa kwenye:\n{save_path}")
                self.log_activity("DOWNLOAD_SUCCESS", f"Imepakua mafanikio kwenda: {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Hitilafu", f"Kimetokea kosa wakati wa kupakua:\n{str(e)}")
                self.log_activity("DOWNLOAD_ERROR", f"Hitilafu ya download: {str(e)}")

    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Chagua Faili za BMPlayer", "", "Media Files (*.mp4 *.mkv *.avi *.mp3 *.wav *.png *.jpg *.jpeg)")
        if files:
            for f in files:
                self.file_paths.append(f)
                self.playlist_widget.addItem(os.path.basename(f))
                self.log_activity("FILE_ADD", f"Imeongeza faili: {os.path.basename(f)}")
            if not self.player.isPlaying() and len(files) > 0:
                self.play_file(0)

    def play_selected_item(self, item):
        row = self.playlist_widget.row(item)
        self.play_file(row)

    def play_file(self, index):
        if 0 <= index < len(self.file_paths):
            path = self.file_paths[index]
            name = os.path.basename(path)
            ext = os.path.splitext(path)[1].lower()
            self.right_tabs.setCurrentIndex(0)
            
            if ext in ['.png', '.jpg', '.jpeg']:
                self.player.stop()
                self.video_widget.hide()
                self.info_viewer.show()
                pixmap = QPixmap(path)
                self.info_viewer.setPixmap(pixmap.scaled(self.info_viewer.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                self.log_activity("VIEW_PICTURE", f"Imeonyesha picha: {name}")
            elif ext in ['.mp3', '.wav']:
                self.video_widget.hide()
                self.info_viewer.show()
                self.info_viewer.setText(f"🎶 INACHEZA AUDIO:\n\n{name}\n\n[ ♪ ♫ ♩ Mziki Unasikika Salama ♩ ♫ ♪ ]")
                self.player.setSource(QUrl.fromLocalFile(path))
                self.player.play()
                self.log_activity("PLAY_AUDIO", f"Inacheza sauti: {name}")
            else:
                self.info_viewer.hide()
                self.video_widget.show()
                self.player.setSource(QUrl.fromLocalFile(path))
                self.player.play()
                self.log_activity("PLAY_VIDEO", f"Inacheza video: {name}")
            self.playlist_widget.setCurrentRow(index)

    def toggle_play_pause(self):
        if self.player.isPlaying(): 
            self.player.pause()
            self.log_activity("PLAYER", "Imeweka Pause")
        else: 
            self.player.play()
            self.log_activity("PLAYER", "Imeweka Play")

    def stop_media(self):
        self.player.stop()
        self.video_widget.show()
        self.info_viewer.hide()
        self.log_activity("PLAYER", "Imeweka Stop")

    def position_changed(self, position): self.slider.setValue(position)
    def duration_changed(self, duration): self.slider.setRange(0, duration)
    def set_position(self, position): self.player.setPosition(position)
    def set_volume(self, volume): self.audio_output.setVolume(volume / 100.0)

    def adjust_volume(self, amount):
        current = int(self.audio_output.volume() * 100)
        new_val = max(0, min(100, current + amount))
        self.audio_output.setVolume(new_val / 100.0)
        self.volume_slider.setValue(new_val)

    def toggle_fullscreen(self):
        if self.isFullScreen(): 
            self.showNormal()
            self.log_activity("VIEW", "Imetoka Skrini Kamili")
        else: 
            self.showFullScreen()
            self.log_activity("VIEW", "Imeweka Skrini Kamili")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if self.right_tabs.currentIndex() == 1:
                return super().eventFilter(obj, event)
            key = event.key()
            if key == Qt.Key.Key_Space:
                self.toggle_play_pause()
                return True
            elif key == Qt.Key.Key_F:
                self.toggle_fullscreen()
                return True
            elif key == Qt.Key.Key_Up:
                self.adjust_volume(10)
                return True
            elif key == Qt.Key.Key_Down:
                self.adjust_volume(-10)
                return True
            elif key == Qt.Key.Key_Right:
                self.player.setPosition(self.player.position() + 5000)
                return True
            elif key == Qt.Key.Key_Left:
                self.player.setPosition(max(0, self.player.position() - 5000))
                return True
        return super().eventFilter(obj, event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(BMPLAYER_STYLE)
    window = BMPlayerApp()
    window.show()
    sys.exit(app.exec())