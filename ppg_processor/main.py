#!/usr/bin/env python3
"""
PPG Processor - A tool for processing PPG data and calculating PPI and HRV metrics
"""

import os
import sys
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from ppg_processor.gui.app import PPGProcessorApp

def main():
    app = QApplication(sys.argv)
    
    # Set app style
    app.setApplicationName("PPG Processor")
    app.setStyle("Breeze")

    # Set application icon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon-512-maskable.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = PPGProcessorApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()