#!/usr/bin/env python3

"""
setup_env.py
------------
macOS AI & Data Science Environment Setup Script
Menu-driven installer for Python virtual environment, data science, and AI packages.

Author: Muhammad Azni Bin Osman
License: MIT License (see below)

MIT License
-----------
Copyright (c) 2025 Muhammad Azni Bin Osman

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import subprocess
import sys
import shutil

# -------------------------------------------
# Helper Functions
# -------------------------------------------

def run_command(cmd):
    """Run a shell command and exit on failure."""
    print(f"\nRunning: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Error: Command failed -> {cmd}")
        sys.exit(1)

def check_python():
    """Check if Python3 is installed, install via Homebrew if missing."""
    if shutil.which("python3") is None:
        print("Python3 not found. Installing Homebrew and Python3...")
        run_command('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
        run_command("brew install python")
    else:
        print(f"Python3 found: {shutil.which('python3')}")

def create_virtual_env(env_name):
    """Create a virtual environment in the current working directory."""
    if not os.path.exists(env_name):
        print(f"Creating virtual environment '{env_name}'...")
        run_command(f"python3 -m venv {env_name}")
    else:
        print(f"Virtual environment '{env_name}' already exists.")
    print(f"Activate it using: source {env_name}/bin/activate")

def install_packages(env_name, packages):
    """Install packages inside the virtual environment with error handling."""
    pip_path = os.path.join(env_name, "bin", "pip")
    try:
        run_command(f"{pip_path} install --upgrade pip")
        pkg_str = " ".join(packages)
        print(f"Installing packages: {pkg_str}")
        run_command(f"{pip_path} install {pkg_str}")
    except Exception as e:
        print(f"Error installing packages: {e}")
        print("Please check dependencies and try again.")

def menu():
    """Display the menu and return the user choice."""
    print("\n=== setup_env.py: AI & Data Science Environment Setup ===")
    print("1. Create virtual environment")
    print("2. Install core data science packages (numpy, pandas, matplotlib, seaborn, scikit-learn, jupyter, plotly)")
    print("3. Install AI/Deep Learning frameworks (PyTorch, TensorFlow, Keras)")
    print("4. Install AI/ML assistant packages (openai, langchain)")
    print("5. Install code quality tools (flake8, black, pylint, autopep8)")
    print("6. Install ALL packages")
    print("7. Exit")
    choice = input("Enter your choice (1-7): ")
    return choice

def install_all(env_name):
    """Install all packages automatically in dependency-safe order."""
    create_virtual_env(env_name)
    print("\nInstalling all packages in dependency-safe order...")
    install_packages(env_name, ["numpy", "pandas", "matplotlib", "seaborn", "scikit-learn", "jupyter", "plotly"])
    install_packages(env_name, ["torch", "torchvision", "torchaudio", "tensorflow", "keras"])
    install_packages(env_name, ["openai", "langchain"])
    install_packages(env_name, ["flake8", "black", "pylint", "autopep8"])
    print("\nAll packages installed successfully!")
    print(f"Activate your virtual environment using: source {env_name}/bin/activate")
    print("Set Cursor IDE's Python interpreter to this environment to start coding.")

# -------------------------------------------
# Main Script
# -------------------------------------------

def main():
    env_name = "dsai_env"
    check_python()

    # Headless mode: auto-install all packages
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        install_all(env_name)
        return

    # Menu-driven mode
    while True:
        choice = menu()

        if choice == "1":
            create_virtual_env(env_name)

        elif choice == "2":
            packages = ["numpy", "pandas", "matplotlib", "seaborn", "scikit-learn", "jupyter", "plotly"]
            install_packages(env_name, packages)

        elif choice == "3":
            packages = ["torch", "torchvision", "torchaudio", "tensorflow", "keras"]
            install_packages(env_name, packages)

        elif choice == "4":
            packages = ["openai", "langchain"]
            install_packages(env_name, packages)

        elif choice == "5":
            packages = ["flake8", "black", "pylint", "autopep8"]
            install_packages(env_name, packages)

        elif choice == "6":
            install_all(env_name)

        elif choice == "7":
            print("Exiting setup_env.py.")
            break

        else:
            print("Invalid choice. Please enter a number from 1-7.")

if __name__ == "__main__":
    main()