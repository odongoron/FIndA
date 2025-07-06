from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from views.main_window import MainWindow
import os
import logging

class FindAApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("FindA")
        self.setApplicationDisplayName("FindA - People Search Engine")
        self.setWindowIcon(QIcon("resources/icons/app_icon.png"))
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("finda.log"),
                logging.StreamHandler()
            ]
        )
        
        self.main_window = MainWindow()
        self.main_window.show()
