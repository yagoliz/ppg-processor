#!/usr/bin/env python3
"""
Build script for PPG Processor using UV instead of setuptools
"""

import os
import platform
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


def ensure_directories():
    """Ensure the resources and assets directories exist"""
    # Define directory paths
    assets_dir = os.path.join("ppg_processor", "assets")
    
    # Create directories if they don't exist
    os.makedirs(assets_dir, exist_ok=True)
    
    # Create __init__.py files if they don't exist
    assets_init = os.path.join(assets_dir, "__init__.py")
    
    if not os.path.exists(assets_init):
        with open(assets_init, "w") as f:
            f.write('"""\nAsset files for the PPG Processor\n"""\n')
    
    print("Directory structure created successfully.")
    
    return assets_dir


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
        "pywavelets",
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

    # Set icon path
    icon_path = os.path.abspath('ppg_processor/assets/icon-512-maskable.png')

    # MacOS specific options
    onefile_option = '--onefile'  # Default to onefile for all platforms
    if platform.system() == 'Darwin':
        onefile_option = '--onedir'

    # Generate spec file
    print("Generating PyInstaller spec file...")
    spec_command = [
        'pyinstaller',
        '--name=PPG_Processor',
        '--windowed',
        "--clean",
        f'{onefile_option}',
        '--collect-submodules=scipy',
        '--collect-submodules=numpy',
        '--collect-submodules=pandas',
        '--collect-submodules=neurokit2',
        '--collect-submodules=PyQt6',
        '--collect-submodules=pyqtgraph',
        f'--icon={icon_path}',
        'ppg_processor/main.py'
    ]
    
    subprocess.run(spec_command, check=True)
    
    # Modify the spec file to include hidden imports and fix issues
    print("Modifying spec file to include required packages...")
    with open('PPG_Processor.spec', 'r') as file:
        spec_content = file.read()
    
    # Add hidden imports for common packages that might be missed
    hidden_imports = [
        'neurokit2',
        'pandas',
        'numpy',
        'pywavelets',
        'scipy.signal',
        'scipy.stats',
        'scipy.interpolate',
        'pyqtgraph',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'sklearn.utils._cython_blas',
        'sklearn.neighbors.typedefs',
        'sklearn.neighbors.quad_tree',
        'sklearn.tree._utils',
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
    print(f"Executable is located at: {os.path.abspath('dist/')}")


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


def create_dmg():
    """Create a DMG installer for macOS"""
    print("Creating DMG installer for macOS...")
    try:
        subprocess.run(["create-dmg",
                        "--volname", "PPG Processor",
                        "--volicon", "ppg_processor/assets/icon-512-maskable.icns",
                        "--window-pos", "200", "120",
                        "--window-size", "800", "400",
                        "--icon-size", "100",
                        "--icon", "PPG_Processor.app", "200", "190",
                        "--hide-extension", "PPG_Processor.app",
                        "--app-drop-link", "600", "185",
                        "PPG_Processor-Installer.dmg",
                        "dist/PPG_Processor.app"],
                        check=True)

    except subprocess.CalledProcessError as e:
        print(f"Error creating DMG: {e}")
        print("Please ensure 'create-dmg' is installed and available in your PATH.")
        sys.exit(1)


def main():
    """Main function to build the application"""
    # Ensure UV is installed
    ensure_uv_installed()
    
    # Ensure directories exist
    ensure_directories()
    
    # Create a virtual environment
    create_virtual_environment()
    
    # Install dependencies
    install_dependencies()
    
    # Build executable
    build_executable()

    # Create dmg if macos
    if platform.system() == 'Darwin':
        create_dmg()
    
    print("\nBuild process completed successfully!")

if __name__ == "__main__":
    main()