from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt5.QtGui import QPixmap, QDesktopServices
from PyQt5.QtCore import Qt, QUrl, QSize
import requests
from io import BytesIO

class ResultItemWidget(QFrame):
    def __init__(self, result_data):
        super().__init__()
        self.result_data = result_data
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("background-color: #2D2D30; border-radius: 6px;")
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Thumbnail
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(80, 80)
        self.thumbnail.setStyleSheet("background-color: #333337; border-radius: 4px;")
        self.load_thumbnail()
        layout.addWidget(self.thumbnail)
        
        # Info section
        info_layout = QVBoxLayout()
        
        # Name and source
        name_layout = QHBoxLayout()
        self.name_label = QLabel(self.result_data.get("name", self.result_data.get("username", "Unknown")))
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #1C97EA;")
        name_layout.addWidget(self.name_label)
        
        name_layout.addStretch()
        
        self.source_label = QLabel(self.result_data.get("source", "Unknown source"))
        self.source_label.setStyleSheet("""
            background-color: #007ACC; 
            color: white; 
            padding: 2px 8px; 
            border-radius: 10px;
            font-size: 12px;
        """)
        name_layout.addWidget(self.source_label)
        info_layout.addLayout(name_layout)
        
        # Details
        if "similarity" in self.result_data:
            similarity = self.result_data["similarity"]
            self.similarity_label = QLabel(f"Similarity: {similarity:.0%}")
            self.similarity_label.setStyleSheet("color: #FFAA00;")
            info_layout.addWidget(self.similarity_label)
        
        # Link
        if "url" in self.result_data:
            self.link_label = QLabel(f"<a href='{self.result_data['url']}' style='color: #1C97EA;'>{self.result_data['url']}</a>")
            self.link_label.setTextFormat(Qt.RichText)
            self.link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.link_label.setOpenExternalLinks(True)
            info_layout.addWidget(self.link_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout, 1)
        
        # View button
        if "url" in self.result_data:
            self.view_btn = QPushButton("🔍 View")
            self.view_btn.setFixedSize(80, 30)
            self.view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #007ACC;
                    color: white;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #1C97EA;
                }
            """)
            self.view_btn.clicked.connect(self.view_result)
            layout.addWidget(self.view_btn)
    
    def load_thumbnail(self):
        # Placeholder for actual thumbnail loading
        if "thumbnail_url" in self.result_data:
            try:
                response = requests.get(self.result_data["thumbnail_url"])
                img_data = BytesIO(response.content)
                pixmap = QPixmap()
                pixmap.loadFromData(img_data.getvalue())
                pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumbnail.setPixmap(pixmap)
                return
            except:
                pass
        
        # Fallback to placeholder
        self.thumbnail.setText("No Image")
        self.thumbnail.setAlignment(Qt.AlignCenter)
    
    def view_result(self):
        if "url" in self.result_data:
            QDesktopServices.openUrl(QUrl(self.result_data["url"]))
