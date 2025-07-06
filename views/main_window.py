from PyQt5.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QLabel, QStatusBar
from PyQt5.QtCore import Qt
from .search_tabs import FaceSearchTab, NameSearchTab
import qdarktheme

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FindA - Find People Across the Internet")
        self.setGeometry(100, 100, 1000, 700)
        
        # Apply dark theme
        qdarktheme.setup_theme("dark")
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header = QLabel("FindA - Find People Across the Internet")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            padding: 20px;
            color: #1C97EA;
        """)
        main_layout.addWidget(header)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Add tabs
        self.face_search_tab = FaceSearchTab()
        self.name_search_tab = NameSearchTab()
        
        self.tab_widget.addTab(self.face_search_tab, "Face Search")
        self.tab_widget.addTab(self.name_search_tab, "Name Search")
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Connect signals
        self.face_search_tab.search_started.connect(self.on_search_started)
        self.face_search_tab.search_completed.connect(self.on_search_completed)
        self.name_search_tab.search_started.connect(self.on_search_started)
        self.name_search_tab.search_completed.connect(self.on_search_completed)
    
    def on_search_started(self, message):
        self.status_bar.showMessage(message)
    
    def on_search_completed(self, results_count):
        self.status_bar.showMessage(f"Search completed. Found {results_count} results.")
