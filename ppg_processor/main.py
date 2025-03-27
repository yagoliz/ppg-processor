#!/usr/bin/env python3
"""
PPG Processor - A tool for processing PPG data and calculating PPI and HRV metrics
"""

import sys
from PyQt6.QtWidgets import QApplication
from ppg_processor.gui.app import PPGProcessorApp

def main():
    app = QApplication(sys.argv)
    
    # Set app style
    app.setStyle("Breeze")
    
    window = PPGProcessorApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()