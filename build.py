#!/usr/bin/env python3
"""
Build script for PPG Processor using UV instead of setuptools
"""

import os
import sys
import subprocess
import shutil

def ensure_uv_installed():
    """Make sure UV is installed"""
    try:
        # Check if uv is already installed
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        print("UV is already installed.")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("UV not found. Installing UV...")
        try:
            # Install UV using the official installer
            curl_command = "curl -sSf https://astral.sh/uv/install.sh | sh"
            subprocess.run(curl_command, shell=True, check=True)
            print("UV installed successfully.")
        except subprocess.SubprocessError:
            print("Failed to install UV automatically.")
            print("Please install UV manually: https://github.com/astral-sh/uv#installation")
            sys.exit(1)

def install_dependencies():
    """Install dependencies using UV"""
    print("Installing dependencies with UV...")
    dependencies = [
        "PyQt6",
        "pyqtgraph",
        "pandas",
        "numpy",
        "scipy",
        "neurokit2",
        "pyinstaller"
    ]
    
    # Create a requirements.txt file
    with open("requirements.txt", "w") as f:
        for dep in dependencies:
            f.write(f"{dep}\n")
    
    # Install dependencies
    subprocess.run(["uv", "pip", "install", "-r", "requirements.txt"], check=True)
    print("Dependencies installed successfully.")

def build_executable():
    """Build executable using PyInstaller"""
    print("Building executable with PyInstaller...")
    
    # Create build directory if it doesn't exist
    if not os.path.exists('build'):
        os.makedirs('build')
    
    # Clean previous builds
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Generate spec file
    print("Generating PyInstaller spec file...")
    spec_command = [
        'pyinstaller',
        '--name=PPG_Processor',
        '--windowed',  # No console window
        '--onefile',   # Single executable file
        'ppg_processor/main.py'
    ]
    
    # Add icon if available
    if os.path.exists('icon.ico'):
        spec_command.append('--icon=icon.ico')
    
    subprocess.run(spec_command, check=True)
    
    # Modify the spec file to include hidden imports
    print("Modifying spec file to include required packages...")
    with open('PPG_Processor.spec', 'r') as file:
        spec_content = file.read()
    
    # Add hidden imports for common packages that might be missed
    hidden_imports = [
        'neurokit2',
        'pandas',
        'numpy',
        'scipy.signal',
        'pyqtgraph',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui'
    ]
    
    # Insert hidden imports into the spec file
    hidden_imports_str = "hiddenimports=" + str(hidden_imports)
    modified_spec = spec_content.replace(
        "hiddenimports=[]",
        hidden_imports_str
    )
    
    with open('PPG_Processor.spec', 'w') as file:
        file.write(modified_spec)
    
    # Build the executable
    print("Building executable with PyInstaller...")
    subprocess.run(['pyinstaller', 'PPG_Processor.spec'], check=True)
    
    print("\nPackaging complete!")
    print(f"Executable is located at: {os.path.abspath('dist/PPG_Processor.exe')}")

def create_virtual_environment():
    """Create a virtual environment using UV"""
    print("Creating a virtual environment with UV...")
    
    # Create a virtual environment in the .venv directory
    subprocess.run(["uv", "venv"], check=True)
    
    print("Virtual environment created successfully in .venv directory.")
    print("To activate the environment:")
    if os.name == 'nt':  # Windows
        print("    .venv\\Scripts\\activate")
    else:  # Unix/Linux/Mac
        print("    source .venv/bin/activate")

def main():
    """Main function to build the application"""
    # Ensure UV is installed
    ensure_uv_installed()
    
    # Create a virtual environment
    create_virtual_environment()
    
    # Install dependencies
    install_dependencies()
    
    # Build executable
    build_executable()
    
    print("\nBuild process completed successfully!")

if __name__ == "__main__":
    main()