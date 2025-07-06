import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QLineEdit, QListWidget, QProgressBar, QListWidgetItem
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from core.search_engine import FindASearch
from .result_item import ResultItemWidget
import threading

logger = logging.getLogger(__name__)

class SearchThread(QThread):
    """Thread for running searches in the background"""
    search_completed = pyqtSignal(list)
    progress_updated = pyqtSignal(int, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, search_engine, search_type, search_data):
        super().__init__()
        self.search_engine = search_engine
        self.search_type = search_type
        self.search_data = search_data

    def run(self):
        try:
            if self.search_type == "face":
                self.progress_updated.emit(10, "Processing image...")
                results = self.search_engine.search_by_face(self.search_data)
            elif self.search_type == "name":
                self.progress_updated.emit(10, "Searching platforms...")
                results = self.search_engine.search_by_name(self.search_data)
            else:
                results = []
                
            self.progress_updated.emit(100, "Search completed")
            self.search_completed.emit(results)
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            self.error_occurred.emit(str(e))

class FaceSearchTab(QWidget):
    search_started = pyqtSignal(str)
    search_completed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.search_engine = FindASearch()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Image upload section
        upload_layout = QHBoxLayout()
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(300, 300)
        self.image_label.setStyleSheet("""
            background-color: #333337; 
            border: 2px dashed #3F3F46;
            border-radius: 4px;
        """)
        self.image_label.setText("No image selected\n\nClick 'Browse' to select an image")
        self.image_label.setAlignment(Qt.AlignCenter)
        upload_layout.addWidget(self.image_label)
        
        # Upload controls
        controls_layout = QVBoxLayout()
        
        self.browse_btn = QPushButton("📁 Browse Image")
        self.browse_btn.clicked.connect(self.browse_image)
        controls_layout.addWidget(self.browse_btn)
        
        self.search_btn = QPushButton("🔍 Start Face Search")
        self.search_btn.setEnabled(False)
        self.search_btn.clicked.connect(self.start_search)
        controls_layout.addWidget(self.search_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        controls_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        controls_layout.addWidget(self.progress_label)
        
        controls_layout.addStretch()
        upload_layout.addLayout(controls_layout)
        layout.addLayout(upload_layout)
        
        # Results section
        results_layout = QVBoxLayout()
        results_layout.addWidget(QLabel("Search Results:"))
        
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                background-color: #252526;
                border: 1px solid #3F3F46;
                border-radius: 4px;
            }
            QListWidget::item {
                border-bottom: 1px solid #3F3F46;
            }
        """)
        self.results_list.setWordWrap(True)
        results_layout.addWidget(self.results_list)
        
        layout.addLayout(results_layout)
    
    def browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Face Image", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.image_path = file_path
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(pixmap)
                self.search_btn.setEnabled(True)
    
    def start_search(self):
        if hasattr(self, 'image_path'):
            self.search_started.emit("Starting face search...")
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_label.setText("Initializing...")
            self.search_btn.setEnabled(False)
            self.browse_btn.setEnabled(False)
            self.results_list.clear()
            
            # Read image as bytes
            with open(self.image_path, "rb") as f:
                image_bytes = f.read()
            
            # Start search thread
            self.search_thread = SearchThread(self.search_engine, "face", image_bytes)
            self.search_thread.search_completed.connect(self.display_results)
            self.search_thread.progress_updated.connect(self.update_progress)
            self.search_thread.error_occurred.connect(self.handle_error)
            self.search_thread.start()
    
    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def display_results(self, results):
        self.search_completed.emit(len(results))
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.search_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        
        for result in results:
            item = QListWidgetItem(self.results_list)
            widget = ResultItemWidget(result)
            item.setSizeHint(widget.sizeHint())
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)
    
    def handle_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"Error: {error_msg}")
        self.progress_label.setStyleSheet("color: #FF5555;")
        self.search_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)

class NameSearchTab(QWidget):
    search_started = pyqtSignal(str)
    search_completed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.search_engine = FindASearch()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Name input section
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Name to Search:"))
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter full name (e.g., John Smith)")
        input_layout.addWidget(self.name_input)
        
        self.search_btn = QPushButton("🔍 Search by Name")
        self.search_btn.clicked.connect(self.start_search)
        input_layout.addWidget(self.search_btn)
        
        layout.addLayout(input_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
        # Results section
        results_layout = QVBoxLayout()
        results_layout.addWidget(QLabel("Search Results:"))
        
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                background-color: #252526;
                border: 1px solid #3F3F46;
                border-radius: 4px;
            }
            QListWidget::item {
                border-bottom: 1px solid #3F3F46;
            }
        """)
        self.results_list.setWordWrap(True)
        results_layout.addWidget(self.results_list)
        
        layout.addLayout(results_layout)
    
    def start_search(self):
        name = self.name_input.text().strip()
        if name:
            self.search_started.emit(f"Searching for '{name}'...")
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_label.setText("Initializing...")
            self.search_btn.setEnabled(False)
            self.name_input.setEnabled(False)
            self.results_list.clear()
            
            # Start search thread
            self.search_thread = SearchThread(self.search_engine, "name", name)
            self.search_thread.search_completed.connect(self.display_results)
            self.search_thread.progress_updated.connect(self.update_progress)
            self.search_thread.error_occurred.connect(self.handle_error)
            self.search_thread.start()
    
    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def display_results(self, results):
        self.search_completed.emit(len(results))
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.search_btn.setEnabled(True)
        self.name_input.setEnabled(True)
        
        for result in results:
            item = QListWidgetItem(self.results_list)
            widget = ResultItemWidget(result)
            item.setSizeHint(widget.sizeHint())
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)
    
    def handle_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"Error: {error_msg}")
        self.progress_label.setStyleSheet("color: #FF5555;")
        self.search_btn.setEnabled(True)
        self.name_input.setEnabled(True)
