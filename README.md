# DSAI Assignments

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Educational-green.svg)](LICENSE)
[![NTU](https://img.shields.io/badge/university-NTU-red.svg)](https://www.ntu.edu.sg/)

Data Science and Artificial Intelligence assignments and coursework for Nanyang Technological University (NTU) SCTP DSAI program.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Setup](#quick-setup)
  - [Environment Profiles](#environment-profiles)
- [DSAI Environment Setup Tool](#dsai-environment-setup-tool)
- [Repository Structure](#repository-structure)
- [Usage Examples](#usage-examples)
- [System Requirements](#system-requirements)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Git Submodules](#git-submodules---course-management)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)
- [Acknowledgments](#acknowledgments)

---

## 🎯 Overview

This repository serves as a centralized hub for NTU DSAI program assignments, projects, and course materials. It features a sophisticated, production-ready environment setup tool (`dsai_env.py`) that automates Python data science environment configuration with intelligent hardware detection and optimization.

**Key Highlights:**
- 🔧 Automated environment setup with multiple pre-configured profiles
- 🖥️ Hardware-aware package selection (Apple Silicon, NVIDIA GPUs)
- 📊 Rich terminal UI with progress tracking and real-time feedback
- 🛡️ Robust error handling with automatic rollback capabilities
- 📝 Comprehensive logging and JSON summary reports
- 🚀 CI/CD ready with non-interactive mode

---

## ✨ Features

### DSAI Environment Setup Tool

The `dsai_env.py` utility is a professional-grade, single-file Python tool designed for best practices in environment management:

#### **Core Capabilities**

| Feature | Description |
|---------|-------------|
| **Hardware Detection** | Automatically detects CPU architecture, GPU availability, RAM, and disk space |
| **Smart Package Selection** | Chooses optimal packages based on detected hardware (e.g., CUDA-enabled PyTorch for NVIDIA GPUs) |
| **Multiple Profiles** | 6 pre-configured profiles for different workflows (data science, deep learning, cloud ML, etc.) |
| **Environment Managers** | Support for conda, venv, or system Python installations |
| **Rich UI** | Beautiful terminal interface with progress bars, spinners, and formatted tables |
| **Error Resilience** | Timeout protection, validation checks, and automatic rollback on failures |
| **Logging** | Detailed logs with verbosity control and JSON summary exports |
| **Dry-Run Mode** | Preview all actions without making system changes |
| **Automation Ready** | Non-interactive mode for CI/CD pipelines and scripts |

#### **Advanced Features**

- **Package Validation**: Security-focused package name validation before installation
- **Dependency Checking**: Pre-installation verification of pip, internet connectivity, and disk space
- **Post-Installation Verification**: Automatic verification of installed packages
- **Critical Package Protection**: Special handling for essential packages with rollback on failure
- **Hardware Hints**: Contextual recommendations based on system configuration
- **Timeout Management**: Configurable timeouts for long-running operations
- **Cross-Platform**: Works seamlessly on macOS, Linux, and Windows

---

## 🚀 Getting Started

### Prerequisites

Before using the DSAI environment setup tool, ensure you have:

- **Python**: Version 3.11 or higher
- **Package Manager**: pip (included with Python) or conda/miniconda
- **Git**: Recommended for version control
- **Disk Space**: Minimum 2 GB free (5+ GB recommended)
- **RAM**: 4 GB minimum (8+ GB recommended for deep learning)

### Quick Setup

#### **Option 1: Automated Setup (Recommended)**

Run the setup tool with the default DSAI assignment profile:

```bash
python dsai_env.py
```

This will:
1. Detect your system hardware and software
2. Display a comprehensive system information table
3. Create an optimized environment with all necessary packages
4. Generate detailed logs and summary reports

#### **Option 2: Choose a Specific Profile**

```bash
# Standard data science environment
python dsai_env.py --profile standard_ds

# Deep learning with hardware optimization
python dsai_env.py --profile deep_learning

# Minimal installation for quick tasks
python dsai_env.py --profile minimal
```

#### **Option 3: Preview Before Installing (Dry Run)**

```bash
python dsai_env.py --dry-run
```

This shows exactly what will be installed without making any changes.

#### **Option 4: Fully Automated (Non-Interactive)**

```bash
python dsai_env.py --non-interactive --profile dsai_assignment
```

Perfect for scripts, CI/CD pipelines, or automated deployments.

### Environment Profiles

The tool includes 6 carefully crafted profiles optimized for different use cases:

| Profile | Description | Primary Packages | Use Case |
|---------|-------------|------------------|----------|
| **`dsai_assignment`** | Default NTU DSAI coursework profile | NumPy, Pandas, Scikit-learn, TensorFlow, PyTorch, OpenCV, NLTK, spaCy | Complete coursework environment |
| **`standard_ds`** | General data science stack | NumPy, Pandas, Scikit-learn, Matplotlib, JupyterLab | Standard analytics and ML |
| **`deep_learning`** | Hardware-aware deep learning | PyTorch/TensorFlow (CUDA/MPS enabled), NumPy, Matplotlib | Neural networks and DL research |
| **`cloud_ml`** | Cloud & MLOps toolkit | AWS/GCP/Azure SDKs, MLflow, Docker, FastAPI | Cloud deployments and MLOps |
| **`minimal`** | Lightweight environment | NumPy, Pandas, pytest | Quick prototyping and testing |
| **`custom`** | Interactive custom selection | User-defined packages | Flexible custom workflows |

---

## 🛠️ DSAI Environment Setup Tool

### Command-Line Interface

```bash
python dsai_env.py [OPTIONS]
```

### Available Options

| Option | Short | Values | Default | Description |
|--------|-------|--------|---------|-------------|
| `--profile` | `-p` | `dsai_assignment`, `standard_ds`, `deep_learning`, `cloud_ml`, `minimal`, `custom` | `dsai_assignment` | Select installation profile |
| `--env` | - | `conda`, `venv`, `system` | Auto-detect | Choose environment manager |
| `--non-interactive` | - | flag | `False` | Run without user prompts |
| `--dry-run` | - | flag | `False` | Preview without making changes |
| `--verbose` | - | flag | `False` | Enable detailed debug logging |
| `--timeout` | - | seconds | `1800` | Timeout for long operations |

### Usage Examples

**Interactive Setup with Profile Selection:**
```bash
python dsai_env.py
# Displays menu to choose profile, environment type, and packages
```

**Automated Deep Learning Environment:**
```bash
python dsai_env.py --profile deep_learning --env conda --non-interactive
```

**Preview Cloud ML Installation:**
```bash
python dsai_env.py --profile cloud_ml --dry-run --verbose
```

**Custom Installation with Extended Timeout:**
```bash
python dsai_env.py --profile custom --timeout 3600
```

### What Happens During Setup

1. **System Detection**
   - Detects OS, architecture, CPU count, RAM, and disk space
   - Checks for NVIDIA GPU or Apple Silicon
   - Identifies installed tools (Git, Conda, Docker)

2. **Profile Selection & Optimization**
   - Loads selected profile configuration
   - Adjusts packages based on hardware capabilities
   - Provides hardware-specific recommendations

3. **Environment Creation**
   - Creates conda environment, venv, or uses system Python
   - Configures appropriate Python version

4. **Pre-Installation Validation**
   - Verifies pip availability
   - Tests internet connectivity to PyPI
   - Checks disk space requirements

5. **Package Installation**
   - Installs packages with progress tracking
   - Handles failures gracefully with retry logic
   - Supports automatic rollback on critical errors

6. **Post-Installation Verification**
   - Validates all installed packages
   - Generates installation summary report
   - Creates detailed logs for troubleshooting

7. **Summary & Activation**
   - Displays installation summary
   - Provides environment activation instructions
   - Exports JSON report (`dsai_env_summary.json`)

---

## 📁 Repository Structure

```
DSAI-Assignments/
├── README.md                          # This comprehensive documentation
├── dsai_env.py                        # Main environment setup tool
├── dsai_env.log                       # Execution logs (auto-generated)
├── dsai_env_summary.json              # Installation summary report (auto-generated)
├── .gitignore                         # Git ignore patterns
└── courses/                           # Course-specific materials
    └── 5m-data-1.1-intro-data-science/
        ├── assignment.py              # Python assignment solutions
        └── dsai_env.py                # Course-specific environment setup
```

### Key Files

- **`dsai_env.py`**: 1174-line production-ready environment setup tool with comprehensive error handling
- **`dsai_env.log`**: Timestamped logs of all setup operations with INFO, WARN, ERROR, and DEBUG levels
- **`dsai_env_summary.json`**: Structured JSON report containing system info, installed packages, and verification results
- **`courses/`**: Directory containing course-specific assignments and materials

---

## 💻 Usage Examples

### Activating Your Environment

After successful setup, activate your environment:

**For Conda Environments:**
```bash
conda activate dsai_env
```

**For venv Environments:**
```bash
# macOS/Linux
source dsai_env/bin/activate

# Windows
dsai_env\Scripts\activate
```

**For System Python:**
No activation needed - packages are installed globally.

### Working with Course Assignments

```bash
# Navigate to course directory
cd courses/5m-data-1.1-intro-data-science/

# Run assignment with doctests
python assignment.py

# Run in verbose mode
python assignment.py -v
```

### Verifying Installation

**Check Installed Packages:**
```bash
pip list | grep -E "numpy|pandas|sklearn|torch|tensorflow"
```

**Test Key Imports:**
```bash
python -c "
import numpy as np
import pandas as pd
import sklearn
import torch
import tensorflow as tf
print('✓ All core packages imported successfully!')
print(f'NumPy: {np.__version__}')
print(f'Pandas: {pd.__version__}')
print(f'PyTorch: {torch.__version__}')
print(f'TensorFlow: {tf.__version__}')
"
```

**Verify GPU Support:**
```bash
# Check PyTorch GPU
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'MPS available: {torch.backends.mps.is_available()}')"

# Check TensorFlow GPU
python -c "import tensorflow as tf; print(f'GPU devices: {tf.config.list_physical_devices(\"GPU\")}')"
```

### Reviewing Installation Logs

**View Summary Report:**
```bash
cat dsai_env_summary.json | python -m json.tool
```

**Check Installation Logs:**
```bash
# View recent logs
tail -50 dsai_env.log

# Search for errors
grep ERROR dsai_env.log

# Search for specific package
grep "torch" dsai_env.log
```

---

## ⚙️ System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | macOS 10.14+, Ubuntu 18.04+, Windows 10+ |
| **Python** | 3.11 or higher |
| **RAM** | 4 GB (8 GB for deep learning) |
| **Disk Space** | 2 GB free (5+ GB for deep learning) |
| **Internet** | Required for package downloads |

### Recommended Configuration

| Component | Recommendation |
|-----------|----------------|
| **OS** | macOS 12+, Ubuntu 20.04+, Windows 11 |
| **Python** | 3.11 or 3.12 |
| **RAM** | 16 GB or more |
| **Disk Space** | 10+ GB free (SSD preferred) |
| **GPU** | NVIDIA GPU with CUDA 11.8+ or Apple Silicon |
| **CPU** | Multi-core processor (4+ cores) |

### Installed Packages by Profile

**`dsai_assignment` Profile Includes:**

**Core Data Science:**
- NumPy 1.24+
- Pandas 2.0+
- SciPy 1.10+
- Scikit-learn 1.3+
- Matplotlib 3.7+
- Seaborn 0.12+
- Plotly 5.14+

**Deep Learning:**
- TensorFlow 2.13+
- PyTorch 2.0+ (with torchvision)

**Computer Vision & NLP:**
- OpenCV (opencv-python) 4.8+
- NLTK 3.8+
- spaCy 3.6+

**Web & Data Collection:**
- Requests 2.31+
- BeautifulSoup4 4.12+

**Development Environment:**
- JupyterLab 4.0+
- Jupyter Notebook 7.0+
- IPython kernel

**Development Tools:**
- pytest 7.4+
- black (code formatter)
- isort (import sorter)
- flake8 (linter)
- pre-commit hooks

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### **Issue: Installation Timeout**

**Symptoms:** Package installation stops or times out

**Solutions:**
```bash
# Increase timeout to 1 hour
python dsai_env.py --timeout 3600

# Use minimal profile first
python dsai_env.py --profile minimal

# Check internet connection
ping pypi.org
```

#### **Issue: Low Disk Space**

**Symptoms:** Installation fails with disk space errors

**Solutions:**
```bash
# Check available space
df -h .

# Use minimal profile
python dsai_env.py --profile minimal

# Clean pip cache
pip cache purge

# Clean conda cache (if using conda)
conda clean --all
```

#### **Issue: Package Installation Failures**

**Symptoms:** Some packages fail to install

**Solutions:**
```bash
# Check detailed logs
cat dsai_env.log | grep ERROR

# Review failed packages in summary
cat dsai_env_summary.json

# Try with verbose logging
python dsai_env.py --verbose

# Install failed packages manually
pip install <package-name>
```

#### **Issue: Apple Silicon Compatibility**

**Symptoms:** Packages fail on M1/M2/M3 Macs

**Solutions:**
```bash
# The tool auto-detects Apple Silicon, but if issues persist:

# Use Miniforge (preferred for Apple Silicon)
# Download from: https://github.com/conda-forge/miniforge

# Ensure you're using ARM64 Python
python -c "import platform; print(platform.machine())"
# Should output: arm64

# Force reinstall with conda-forge
conda install -c conda-forge <package-name>
```

#### **Issue: NVIDIA CUDA Not Detected**

**Symptoms:** PyTorch/TensorFlow don't detect GPU

**Solutions:**
```bash
# Verify NVIDIA drivers
nvidia-smi

# Check CUDA version
nvcc --version

# Install CUDA-specific PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify GPU in Python
python -c "import torch; print(torch.cuda.is_available())"
```

#### **Issue: Permission Denied**

**Symptoms:** Cannot create environment or install packages

**Solutions:**
```bash
# Use venv instead of system Python
python dsai_env.py --env venv

# Or use conda
python dsai_env.py --env conda

# For system Python (not recommended), use:
pip install --user <package-name>
```

### Getting Help

1. **Check Logs**: Review `dsai_env.log` for detailed error messages
2. **Review Summary**: Examine `dsai_env_summary.json` for installation status
3. **Verbose Mode**: Run with `--verbose` flag for debugging
4. **Dry Run**: Use `--dry-run` to preview actions without making changes
5. **System Info**: Verify system meets minimum requirements

---

## 🔬 Development

### Running in Development Mode

**Enable Detailed Logging:**
```bash
python dsai_env.py --verbose --profile custom
```

**Test Without Making Changes:**
```bash
python dsai_env.py --dry-run --profile deep_learning --verbose
```

**Rapid Testing with Minimal Profile:**
```bash
python dsai_env.py --profile minimal --non-interactive
```

### Extending Profiles

You can create custom profiles by editing the `PROFILES` dictionary in `dsai_env.py`:

```python
PROFILES: Dict[str, Dict[str, Any]] = {
    # ... existing profiles ...

    "my_custom_profile": {
        "description": "Custom profile for my specific needs",
        "python": "3.11",
        "packages": [
            "numpy",
            "pandas",
            "requests",
            "flask",
            "sqlalchemy",
        ],
        "dev_packages": [
            "pytest",
            "black",
            "mypy",
        ],
    },
}
```

Then run:
```bash
python dsai_env.py --profile my_custom_profile
```

### Adding Hardware Rules

Add custom hardware detection rules in the `HARDWARE_RULES` dictionary:

```python
HARDWARE_RULES: Dict[str, Dict[str, str]] = {
    # ... existing rules ...

    "my_custom_hardware": {
        "hint": "Custom hint for specific hardware configuration",
    },
}
```

### Tool Architecture

The `dsai_env.py` tool follows a class-driven architecture:

- **`SetupLogger`**: Thread-safe logging with Rich console support
- **`SubprocessRunner`**: Safe subprocess execution with timeout management
- **`SystemDetector`**: Comprehensive hardware and software detection
- **`UserInterface`**: Rich terminal UI with DSAI branding
- **`EnvironmentManager`**: Virtual environment creation and management
- **`EnvironmentValidator`**: Dependency checking and package verification
- **`PackageInstaller`**: Package installation with progress tracking and rollback
- **`ConfigManager`**: Profile and hardware configuration management
- **`SetupOrchestrator`**: Main workflow coordinator with error handling

---

## 🤝 Contributing

This repository contains coursework and personal assignments for the NTU SCTP DSAI program. While this is primarily an educational repository:

- **Suggestions Welcome**: Feel free to suggest improvements to the environment setup tool
- **Bug Reports**: Report any issues you encounter with the setup process
- **Feature Requests**: Suggest new profiles or features that would benefit other students

**Note**: Please do not submit solutions to course assignments.

---

## 📄 License

This project is for **educational purposes only** as part of NTU SCTP DSAI coursework.

All code and materials are provided for learning and reference. Please adhere to NTU's academic integrity policies when using this repository.

---

## 👤 Author

**Muhammad Azni Osman**

- NTU SCTP DSAI Program Student
- GitHub: [@azniosman](https://github.com/azniosman/) *(if applicable)*

---

## 🙏 Acknowledgments

- **Nanyang Technological University** - SCTP DSAI Program curriculum and support
- **Open-Source Community** - NumPy, Pandas, Scikit-learn, PyTorch, TensorFlow, and countless other libraries
- **Rich Library** - Beautiful terminal formatting and UI ([Textualize/rich](https://github.com/Textualize/rich))
- **psutil** - Cross-platform system and process utilities ([giampaolo/psutil](https://github.com/giampaolo/psutil))
- **Python Community** - For excellent documentation and support

### Technology Stack

| Category | Technologies |
|----------|-------------|
| **Language** | Python 3.11+ |
| **Data Science** | NumPy, Pandas, SciPy, Scikit-learn |
| **Deep Learning** | PyTorch, TensorFlow |
| **Visualization** | Matplotlib, Seaborn, Plotly |
| **NLP** | NLTK, spaCy |
| **Computer Vision** | OpenCV |
| **Development** | JupyterLab, pytest, black, flake8 |
| **UI** | Rich (terminal UI library) |
| **System** | psutil (system information) |

---

## 📊 Project Status

- ✅ **Environment Setup Tool**: Production-ready
- ✅ **Documentation**: Comprehensive
- 🔄 **Course Materials**: Ongoing (updated per semester)
- 🔄 **Assignments**: In progress

---

## 📝 Additional Notes

### Auto-Generated Files

The environment setup tool automatically generates the following files:

1. **`dsai_env.log`**: Timestamped logs with detailed operation history
   - INFO: General information and progress
   - WARN: Warnings and non-critical issues
   - ERROR: Errors and failures
   - DEBUG: Detailed debugging information (with `--verbose`)

2. **`dsai_env_summary.json`**: Structured installation report containing:
   - Start and end timestamps
   - Selected profile and environment type
   - System information (OS, hardware, Python version)
   - Package installation results (success/failure for each)
   - Post-installation verification results
   - Error messages and warnings

### Git Submodules - Course Management

This repository uses **Git submodules** to manage course repositories as separate entities while maintaining clean version control.

#### **Daily Workflow**

**Working on course assignments:**
```bash
# Navigate to course folder
cd courses/5m-data-1.1-intro-data-science/

# Make changes and commit within the course repo
git add .
git commit -m "completed assignment 1"
git push origin main

# Return to parent repo and update submodule reference
cd ../..
git add courses/5m-data-1.1-intro-data-science
git commit -m "update: course progress"
git push origin main
```

#### **Cloning This Repository**

When cloning on a new machine, initialize submodules:
```bash
# Clone with submodules in one command
git clone --recurse-submodules <repo-url>

# OR clone first, then initialize submodules
git clone <repo-url>
cd DSAI-Assignments
git submodule update --init --recursive
```

#### **Updating Course Content**

**Pull latest changes from course fork:**
```bash
cd courses/5m-data-1.1-intro-data-science/
git pull origin main
cd ../..
git add courses/5m-data-1.1-intro-data-science
git commit -m "update: pulled latest course materials"
```

**Update all submodules at once:**
```bash
git submodule update --remote --merge
git add .
git commit -m "update: all course submodules"
```

#### **Adding New Course Submodules**

```bash
# Add a new course repository
git submodule add <your-fork-url> courses/<course-name>
git commit -m "add: <course-name> submodule"
git push origin main
```

#### **Useful Submodule Commands**

```bash
# Check submodule status
git submodule status

# View submodule configuration
cat .gitmodules

# Remove a submodule (if needed)
git submodule deinit courses/<course-name>
git rm courses/<course-name>
rm -rf .git/modules/courses/<course-name>
```

### Best Practices

- **Always use virtual environments** (conda or venv) instead of system Python
- **Review logs** after installation to ensure all packages installed correctly
- **Keep environments separate** for different projects to avoid dependency conflicts
- **Update regularly** but test in a separate environment first
- **Use version control** (Git) to track changes to your code
- **Commit submodule changes separately** from parent repo changes for clarity

### Performance Tips

- **SSD recommended** for faster package installation
- **Stable internet** ensures reliable downloads from PyPI
- **Sufficient RAM** prevents out-of-memory errors during installation
- **GPU acceleration** significantly speeds up deep learning tasks

---

**Happy Learning! 🎓📊🤖**

*Last updated: October 2025*
