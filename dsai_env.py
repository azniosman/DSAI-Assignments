#!/usr/bin/env python3
"""
Refactored Profile-driven AI & Data Science Environment Setup Tool
Best-practice, single-file, class-driven design.

Features:
- Centralized config for profiles and hardware rules
- Classes with single responsibilities:
  SetupLogger, SubprocessRunner, SystemDetector, UserInterface,
  ConfigManager, EnvironmentManager, PackageResolver, PackageInstaller,
  GitManager, ProjectScaffolder, IDEManager, SetupOrchestrator
- Dry-run mode (--dry-run) to preview actions
- Non-interactive automation and interactive prompts with rich fallback
- Robust logging to console and file with verbosity control
- Timeout-protected subprocess calls with safe shell usage
- Final JSON summary written to disk
- Built-in 'validate' passive checks for CI usage (--validate)
- Extra CLI flags for common flows

Author: Refactor requested by user (Azni). Extensive comments and docstrings included.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# Optional third-party libs (rich for nice UI, psutil for system info)
try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except Exception:
    RICH_AVAILABLE = False

try:
    import psutil  # type: ignore
    PSUTIL_AVAILABLE = True
except Exception:
    PSUTIL_AVAILABLE = False



# Default values for timeouts and filenames
DEFAULT_LOG_FILE = "setup_ds_env.refactor.log"
DEFAULT_TIMEOUT = 1800  # seconds for long operations (30 minutes)
SUMMARY_FILE = "setup_summary.json"

# -----------------------
# Utility classes
# -----------------------


class SetupLogger:
    """
    Lightweight logger that writes to both console (with optional rich colors) and to a file.
    Includes levels: INFO, WARN, ERROR, DEBUG.
    """

    def __init__(self, log_path: Union[str, Path] = DEFAULT_LOG_FILE, verbose: bool = False) -> None:
        """
        Initialize logger.

        :param log_path: path to the log file
        :param verbose: if True, include DEBUG logs
        """
        self.log_path = Path(log_path)
        self.verbose = verbose
        self._lock = threading.Lock()
        self._ensure_log_dir()
        self._start_time = time.time()
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None
        self._log("INFO", "Logger initialized.")

    def _ensure_log_dir(self) -> None:
        """Ensure the directory for the log file exists."""
        try:
            if not self.log_path.parent.exists():
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass  # best-effort; we will handle write errors elsewhere

    def _timestamp(self) -> str:
        """Return current timestamp string for logs."""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _log(self, level: str, message: str) -> None:
        """
        Internal method to write a log line to console and file.

        :param level: log level string
        :param message: message to log
        """
        line = f"{self._timestamp()} [{level}] {message}"
        with self._lock:
            # Console output
            try:
                if self.console:
                    if level == "ERROR":
                        self.console.print(f"[bold red]{line}[/]")
                    elif level == "WARN":
                        self.console.print(f"[yellow]{line}[/]")
                    elif level == "DEBUG" and self.verbose:
                        self.console.print(f"[dim]{line}[/]")
                    else:
                        self.console.print(line)
                else:
                    if level == "ERROR":
                        print(line, file=sys.stderr)
                    else:
                        print(line)
            except Exception:
                # Console logging should not crash the program
                pass

            # File append
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                # If writing to file fails, print minimal info and continue
                print(f"{self._timestamp()} [WARN] Failed to write to log file {self.log_path}", file=sys.stderr)

    def info(self, msg: str) -> None:
        """Log an informational message."""
        self._log("INFO", msg)

    def warn(self, msg: str) -> None:
        """Log a warning."""
        self._log("WARN", msg)

    def error(self, msg: str) -> None:
        """Log an error."""
        self._log("ERROR", msg)

    def debug(self, msg: str) -> None:
        """Log a debug message, only if verbose is enabled."""
        if self.verbose:
            self._log("DEBUG", msg)


class SubprocessRunner:
    """
    A safe wrapper to run subprocesses with timeouts and standardized logging.
    Uses list-style arguments to avoid shell injection.
    """

    def __init__(self, logger: SetupLogger, dry_run: bool = False, timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        :param logger: SetupLogger for logs
        :param dry_run: if True, do not execute commands, only log them
        :param timeout: default timeout for commands
        """
        self.logger = logger
        self.dry_run = dry_run
        self.timeout = timeout

    def run(self, cmd: Sequence[str], check: bool = True, capture_output: bool = False) -> Tuple[int, str, str]:
        """
        Run a subprocess command safely.

        :param cmd: command list (no shell)
        :param check: if True, raise CalledProcessError on non-zero exit
        :param capture_output: if True, capture stdout/stderr and return them
        :return: (returncode, stdout, stderr)
        """
        self.logger.debug(f"Executing command: {' '.join(cmd)} (dry_run={self.dry_run})")
        if self.dry_run:
            return 0, f"DRY_RUN: {' '.join(cmd)}", ""

        try:
            proc = subprocess.run(
                list(cmd),
                capture_output=capture_output,
                text=True,
                timeout=self.timeout,
                check=check,
            )
            return proc.returncode, proc.stdout.strip() if proc.stdout else "", proc.stderr.strip() if proc.stderr else ""
        except subprocess.TimeoutExpired as te:
            self.logger.error(f"Command timed out after {self.timeout} seconds: {' '.join(cmd)}")
            raise
        except subprocess.CalledProcessError as cpe:
            self.logger.error(f"Command failed: {' '.join(cmd)}; returncode={cpe.returncode}")
            if cpe.stdout:
                self.logger.error(f"STDOUT: {cpe.stdout.strip()}")
            if cpe.stderr:
                self.logger.error(f"STDERR: {cpe.stderr.strip()}")
            raise

# -----------------------
# System detection
# -----------------------


@dataclass
class SystemInfo:
    """
    Data class holding system detection results.
    """
    os_name: str
    os_version: str
    machine: str
    cpu_count: int
    total_ram_gb: float
    free_disk_gb: float
    has_nvidia: bool
    has_apple_silicon: bool
    python_version: str
    git_version: Optional[str] = None
    conda_version: Optional[str] = None
    docker_version: Optional[str] = None


class SystemDetector:
    """
    Detect the host OS/hardware and installed developer tools.
    """

    def __init__(self, logger: SetupLogger, runner: SubprocessRunner) -> None:
        """
        :param logger: SetupLogger
        :param runner: SubprocessRunner for running tool checks
        """
        self.logger = logger
        self.runner = runner

    def detect(self) -> SystemInfo:
        """Detect system properties and return a SystemInfo instance."""
        self.logger.info("Detecting system hardware and environment...")
        os_name = platform.system()
        os_version = platform.version()
        machine = platform.machine()
        cpu_count = os.cpu_count() or 1
        self.logger.debug(f"os={os_name}, machine={machine}, cpu_count={cpu_count}")

        # RAM detection: prefer psutil; fallback to platform-specific heuristics
        total_ram_gb = self._get_total_ram_gb()

        # Disk free space on current working dir
        try:
            usage = shutil.disk_usage(os.getcwd())
            free_disk_gb = usage.free / (1024 ** 3)
        except Exception:
            free_disk_gb = 0.0
        self.logger.debug(f"free_disk_gb={free_disk_gb:.2f}")

        # GPU detection: check nvidia-smi, also Apple Silicon heuristics
        has_nvidia = shutil.which("nvidia-smi") is not None
        has_apple_silicon = "arm" in machine.lower() or "apple" in platform.processor().lower()

        # Tool versions
        python_version = platform.python_version()
        git_version = self._run_version(["git", "--version"])
        conda_version = self._run_version(["conda", "--version"])
        docker_version = self._run_version(["docker", "--version"])

        info = SystemInfo(
            os_name=os_name,
            os_version=os_version,
            machine=machine,
            cpu_count=cpu_count,
            total_ram_gb=round(total_ram_gb, 2),
            free_disk_gb=round(free_disk_gb, 2),
            has_nvidia=has_nvidia,
            has_apple_silicon=has_apple_silicon,
            python_version=python_version,
            git_version=git_version,
            conda_version=conda_version,
            docker_version=docker_version,
        )
        self.logger.info("System detection complete.")
        self.logger.debug(f"SystemInfo: {info}")
        return info

    def _get_total_ram_gb(self) -> float:
        """Return total RAM in GB, using psutil if available, else heuristics."""
        if PSUTIL_AVAILABLE:
            try:
                return psutil.virtual_memory().total / (1024 ** 3)
            except Exception:
                self.logger.debug("psutil present but failed to read memory.")

        system = platform.system()
        if system == "Darwin":
            try:
                out = subprocess.check_output(["sysctl", "-n", "hw.memsize"])
                return int(out) / (1024 ** 3)
            except Exception:
                pass
        elif system == "Linux":
            try:
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            return int(line.split()[1]) / (1024 ** 2)
            except Exception:
                pass
        return 4.0  # Conservative default

    def _run_version(self, cmd: Sequence[str]) -> Optional[str]:
        """Run a small command to capture tool version. Return None on failure."""
        if shutil.which(cmd[0]) is None:
            return None
        try:
            rc, out, err = self.runner.run(cmd, check=True, capture_output=True)
            # prefer stdout then stderr
            return (out or err).strip()
        except Exception:
            return None

# -----------------------
# UI handling (rich or plain)
# -----------------------


class UserInterface:
    """
    Handles interactive prompts and progress displays.
    Wraps rich UI when available with a plain fallback.
    """

    def __init__(self, logger: SetupLogger) -> None:
        """
        Initialize UI with a logger.

        :param logger: SetupLogger instance
        """
        self.logger = logger
        self.rich = RICH_AVAILABLE
        self.console = Console() if self.rich else None

    def choose_profile(self, default: str, profiles: Dict[str, Dict[str, Any]], non_interactive: bool) -> str:
        """
        Ask the user to choose a profile. Return the chosen profile name.

        :param default: default profile name to fall back to
        :param profiles: the profiles dict to present
        :param non_interactive: if True, do not prompt and return default
        """
        if non_interactive:
            self.logger.info(f"Non-interactive mode: selecting default profile '{default}'")
            return default

        keys = list(profiles.keys())
        if self.rich and self.console:
            table = Table(title="Available Profiles")
            table.add_column("Index", justify="right")
            table.add_column("Profile")
            table.add_column("Description")
            for idx, name in enumerate(keys, start=1):
                table.add_row(str(idx), name, profiles[name].get("description", ""))
            self.console.print(table)
            choice = Prompt.ask("Choose profile (index or name)", default=default)
        else:
            print("Profiles:")
            for idx, name in enumerate(keys, start=1):
                print(f"  {idx}. {name} - {profiles[name].get('description','')}")
            choice = input(f"Select profile (index or name) [{default}]: ").strip() or default

        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            return keys[int(choice) - 1]
        if choice in keys:
            return choice

        self.logger.warn(f"Invalid choice '{choice}', defaulting to '{default}'")
        return default

    def confirm(self, message: str, default: bool = True, non_interactive: bool = False) -> bool:
        """
        Ask a yes/no question. Respects non-interactive mode by returning default.
        """
        if non_interactive:
            self.logger.info(f"Non-interactive: defaulting confirmation '{message}' -> {default}")
            return default
        if self.rich:
            return Confirm.ask(message, default=default)
        else:
            resp = input(f"{message} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
            if resp == "":
                return default
            return resp in ("y", "yes")

    def prompt_text(self, message: str, default: Optional[str] = None, non_interactive: bool = False) -> str:
        """
        Prompt for a text value with default. In non-interactive mode, returns default or empty string.
        """
        if non_interactive:
            return default or ""
        if self.rich:
            return Prompt.ask(message, default=default)
        else:
            return input(f"{message} [{default or ''}]: ").strip() or (default or "")

    def show_system_info(self, info: SystemInfo) -> None:
        """Nicely print system detection results."""
        if self.rich:
            table = Table(title="System Information")
            table.add_column("Property")
            table.add_column("Value")
            table.add_row("OS", f"{info.os_name} {info.os_version}")
            table.add_row("Machine", info.machine)
            table.add_row("CPUs", str(info.cpu_count))
            table.add_row("Total RAM (GB)", str(info.total_ram_gb))
            table.add_row("Free Disk (GB)", str(info.free_disk_gb))
            table.add_row("NVIDIA GPU", str(info.has_nvidia))
            table.add_row("Apple Silicon", str(info.has_apple_silicon))
            table.add_row("Python", info.python_version)
            table.add_row("Git", info.git_version or "not found")
            table.add_row("Conda", info.conda_version or "not found")
            table.add_row("Docker", info.docker_version or "not found")
            self.console.print(table)
        else:
            print("System information:")
            print(f"  OS: {info.os_name} {info.os_version}")
            print(f"  Machine: {info.machine}")
            print(f"  CPUs: {info.cpu_count}")
            print(f"  Total RAM (GB): {info.total_ram_gb}")
            print(f"  Free Disk (GB): {info.free_disk_gb}")
            print(f"  NVIDIA GPU: {info.has_nvidia}")
            print(f"  Apple Silicon: {info.has_apple_silicon}")
            print(f"  Python: {info.python_version}")
            print(f"  Git: {info.git_version or 'not found'}")
            print(f"  Conda: {info.conda_version or 'not found'}")
            print(f"  Docker: {info.docker_version or 'not found'}")

    def final_summary(self, summary: Dict[str, Any]) -> None:
        """
        Display final summary (JSON style). This is designed to be readable in both modes.
        """
        pretty = json.dumps(summary, indent=2)
        if self.rich:
            self.console.print(Panel(pretty, title="Setup Summary", width=120))
        else:
            print("Setup Summary:")
            print(pretty)

# -----------------------
# Config manager (centralized rules)
# -----------------------


class ConfigManager:
    """
    Encapsulates profile config and hardware rules, plus helper methods.
    """

    PROFILES: Dict[str, Dict[str, Any]] = {
        "standard_ds": {
            "description": "General Data Science: numpy, pandas, scikit-learn, matplotlib, jupyter.",
            "python": "3.11",
            "packages": [
                "numpy",
                "pandas",
                "scipy",
                "scikit-learn",
                "matplotlib",
                "seaborn",
                "jupyterlab",
                "notebook",
                "ipykernel",
                "joblib",
                "tqdm",
                "pydantic",
            ],
            "dev_packages": ["pytest", "black", "isort", "flake8", "pre-commit"],
        },
        "deep_learning": {
            "description": "Deep learning: hardware-aware selection (PyTorch/TensorFlow).",
            "python": "3.11",
            "packages": [
                "numpy",
                "pandas",
                "matplotlib",
                "seaborn",
                "jupyterlab",
                "notebook",
                "ipykernel",
            ],
            "dev_packages": ["pytest", "black", "isort", "flake8", "pre-commit"],
        },
        "cloud_ml": {
            "description": "Cloud & MLOps: AWS/GCP/Azure SDKs, mlflow, docker SDK.",
            "python": "3.11",
            "packages": [
                "numpy",
                "pandas",
                "boto3",
                "google-cloud-storage",
                "azure-storage-blob",
                "mlflow",
                "docker",
                "fastapi",
                "uvicorn",
            ],
            "dev_packages": ["pytest", "black", "isort", "flake8", "pre-commit"],
        },
        "minimal": {
            "description": "Minimal: lightweight environment for quick tasks.",
            "python": "3.11",
            "packages": ["numpy", "pandas"],
            "dev_packages": ["pytest"],
        },
        "custom": {
            "description": "Custom: prompt for packages interactively (or via CLI).",
            "python": None,
            "packages": [],
            "dev_packages": [],
        },
    }

    HARDWARE_RULES: Dict[str, Dict[str, str]] = {
        "apple_silicon": {
            "hint": "Prefer Miniforge/conda-forge and arm64 wheels. Some packages require special builds.",
        },
        "nvidia_cuda": {
            "hint": "Install CUDA-enabled PyTorch via official channels (conda -c pytorch or pip wheel for your CUDA).",
        },
        "intel_cpu": {
            "hint": "Standard x86_64 wheels available via pip/conda.",
        },
        "low_ram": {
            "hint": "Use minimal profile or cloud instances for heavy training tasks.",
        },
    }

    def __init__(self, logger: SetupLogger) -> None:
        """
        :param logger: SetupLogger for logging
        """
        self.logger = logger

    def get_profile(self, name: str) -> Dict[str, Any]:
        """
        Return profile config for 'name'. If missing, raise KeyError.
        """
        if name not in self.PROFILES:
            self.logger.error(f"Profile '{name}' not defined.")
            raise KeyError(f"Profile '{name}' not found")
        return self.PROFILES[name]

    def list_profiles(self) -> List[str]:
        """Return list of available profile names."""
        return list(self.PROFILES.keys())

    def hardware_hint(self, key: str) -> Optional[str]:
        """Return hardware hint from rules if present."""
        return self.HARDWARE_RULES.get(key, {}).get("hint")

# -----------------------
# Environment & package management
# -----------------------


class EnvironmentManager:
    """
    Responsible for creating and managing the Python environment: conda envs or venvs.
    """

    def __init__(self, logger: SetupLogger, runner: SubprocessRunner, dry_run: bool = False) -> None:
        """
        :param logger: SetupLogger
        :param runner: SubprocessRunner to run conda/venv commands
        :param dry_run: if True, do not actually execute creation commands
        """
        self.logger = logger
        self.runner = runner
        self.dry_run = dry_run

    def create_conda_env(self, name: str, python_version: Optional[str] = None, channels: Optional[List[str]] = None) -> bool:
        """
        Create a conda env by running 'conda create -n name python=version -y'.

        Returns True on success; False otherwise. Does nothing if conda is missing.
        """
        # Validate conda presence
        if shutil.which("conda") is None:
            self.logger.warn("Conda not found on PATH; skipping conda env creation.")
            return False
        # Build command
        cmd = ["conda", "create", "-y", "-n", name]
        if python_version:
            cmd.append(f"python={python_version}")
        if channels:
            for ch in channels:
                cmd.extend(["-c", ch])
        try:
            self.logger.info(f"Creating conda environment '{name}' (python={python_version})")
            self.runner.run(cmd, check=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create conda env '{name}': {e}")
            return False

    def create_venv(self, path: Union[str, Path], python_exe: Optional[str] = None) -> bool:
        """
        Create a venv in the given path. Use python_exe if provided.

        Returns True on success.
        """
        path = Path(path)
        if path.exists():
            self.logger.warn(f"venv path '{path}' already exists. Creation skipped.")
            return True
        try:
            cmd = [python_exe or sys.executable, "-m", "venv", str(path)]
            self.logger.info(f"Creating venv at '{path}' (python_exe={python_exe})")
            self.runner.run(cmd, check=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create venv at '{path}': {e}")
            return False

# Package resolver chooses framework variants based on hardware and profile


class PackageResolver:
    """
    Resolve package lists per profile and hardware. Encapsulates all rules for hardware-specific selections.
    """

    def __init__(self, logger: SetupLogger, cfg: ConfigManager, sysinfo: SystemInfo) -> None:
        """
        :param logger: SetupLogger
        :param cfg: ConfigManager holding profile info
        :param sysinfo: detected system info
        """
        self.logger = logger
        self.cfg = cfg
        self.sysinfo = sysinfo

    def resolve(self, profile_name: str, custom_packages: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Produce 'packages' and 'dev_packages' lists for the profile, applying hardware-aware rules.
        """
        self.logger.info(f"Resolving packages for profile '{profile_name}'")
        profile = self.cfg.get_profile(profile_name)
        packages = list(profile.get("packages", []))
        dev_packages = list(profile.get("dev_packages", []))

        if profile_name == "custom" and custom_packages:
            self.logger.debug(f"Adding custom packages: {custom_packages}")
            packages.extend(custom_packages)

        if profile_name == "deep_learning":
            if self.sysinfo.has_nvidia:
                self.logger.info("NVIDIA GPU detected. Recommending CUDA-enabled PyTorch.")
                packages.extend(["torch", "torchvision", "torchaudio"])
            elif self.sysinfo.has_apple_silicon:
                self.logger.info("Apple Silicon detected. Adding torch and tensorflow-metal.")
                packages.extend(["torch", "torchvision", "torchaudio", "tensorflow-macos", "tensorflow-metal"])
            else:
                self.logger.info("No specialized hardware detected. Adding CPU-based deep learning packages.")
                packages.extend(["torch", "torchvision", "torchaudio", "tensorflow-cpu"])

        return {
            "packages": list(dict.fromkeys(packages)),
            "dev_packages": list(dict.fromkeys(dev_packages)),
        }


class PackageInstaller:
    """
    Install packages into conda envs or venvs using either conda or pip with careful error handling.
    """

    def __init__(self, logger: SetupLogger, runner: SubprocessRunner, env_manager: EnvironmentManager, dry_run: bool = False) -> None:
        """
        :param logger: SetupLogger
        :param runner: SubprocessRunner used to execute installs
        :param env_manager: EnvironmentManager used for env detection/creation
        :param dry_run: if True, do not actually perform installs
        """
        self.logger = logger
        self.runner = runner
        self.env_manager = env_manager
        self.dry_run = dry_run

    def install_packages_conda(self, env_name: str, packages: List[str], channels: Optional[List[str]] = None) -> Tuple[bool, List[str]]:
        """
        Install packages into a conda environment using 'conda install -n env -y pkg1 pkg2'.

        Returns (success, failed_packages).
        """
        if shutil.which("conda") is None:
            self.logger.warn("Conda is not available; cannot perform conda installs.")
            return False, packages

        if not packages:
            self.logger.info("No conda packages to install.")
            return True, []

        failed: List[str] = []
        chunk_size = 20
        for i in range(0, len(packages), chunk_size):
            chunk = packages[i : i + chunk_size]
            cmd = ["conda", "install", "-y", "-n", env_name]
            if channels:
                for ch in channels:
                    cmd.extend(["-c", ch])
            cmd.extend(chunk)

            try:
                self.logger.info(f"Conda installing: {', '.join(chunk)}")
                self.runner.run(cmd, check=True)
            except Exception:
                self.logger.error(f"Conda failed to install chunk: {', '.join(chunk)}")
                failed.extend(chunk)

        return not failed, failed

    def install_packages_pip(self, target: str, packages: List[str], venv_path: Optional[Union[str, Path]] = None) -> Tuple[bool, List[str]]:
        """
        Install packages using pip into either:
         - a venv located at venv_path (using that pip); or
         - a conda env by running: conda run -n env pip install ...
         - system python pip if neither provided.

        Returns (success, failed_packages).
        """
        if not packages:
            self.logger.info("No pip packages to install.")
            return True, []

        failed: List[str] = []
        pip_cmd_base: List[str]

        if venv_path and Path(venv_path).exists():
            pip_exe = "pip.exe" if platform.system() == "Windows" else "pip"
            pip_cmd_base = [str(Path(venv_path) / "bin" / pip_exe)]
        elif target and shutil.which("conda") and not Path(target).exists():
            pip_cmd_base = ["conda", "run", "-n", target, "pip"]
        else:
            pip_cmd_base = [sys.executable, "-m", "pip"]

        for pkg in packages:
            try:
                self.logger.info(f"pip installing '{pkg}'")
                self.runner.run(pip_cmd_base + ["install", pkg], check=True)
            except Exception:
                self.logger.error(f"pip failed to install '{pkg}'")
                failed.append(pkg)

        return not failed, failed

    def install_requirements_file(self, target: str, requirements_file: Union[str, Path], venv_path: Optional[Union[str, Path]] = None) -> Tuple[bool, List[str]]:
        """
        Convenience to install packages from a requirements.txt file.
        """
        if not Path(requirements_file).exists():
            self.logger.warn(f"Requirements file '{requirements_file}' not found.")
            return True, []
        # Build pip command similarly to install_packages_pip but with '-r' option
        if venv_path and Path(venv_path).exists():
            pip_path = Path(venv_path) / ("Scripts" if platform.system() == "Windows" else "bin") / "pip"
            cmd = [str(pip_path), "install", "-r", str(requirements_file)]
        elif target and shutil.which("conda") and not Path(target).exists():
            cmd = ["conda", "run", "-n", target, "pip", "install", "-r", str(requirements_file)]
        else:
            cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
        try:
            self.logger.info(f"Installing from requirements file: {requirements_file}")
            self.runner.run(cmd, check=True)
            return True, []
        except Exception:
            self.logger.error("Failed to install requirements from file.")
            return False, [str(requirements_file)]

# -----------------------
# Git & CI setup
# -----------------------


class GitManager:
    """
    Initialize git repository, write .gitignore, set up pre-commit, and optionally write CI workflow YAML.
    """

    def __init__(self, logger: SetupLogger, runner: SubprocessRunner, dry_run: bool = False) -> None:
        self.logger = logger
        self.runner = runner
        self.dry_run = dry_run

    def init_repo(self, path: Union[str, Path], remote: Optional[str] = None) -> bool:
        """
        Initialize a git repo at path. Optionally add a remote origin.
        Returns True on success or if git not present (non-fatal).
        """
        if shutil.which("git") is None:
            self.logger.warn("Git not found; skipping git init.")
            return False

        path = Path(path)
        if (path / ".git").exists():
            self.logger.info(f"Git repository already exists at {path}")
            return True

        try:
            self.logger.info(f"Initializing git repository at {path}")
            self.runner.run(["git", "init"], check=True, capture_output=False)
            if remote:
                self.logger.info(f"Adding remote origin {remote}")
                self.runner.run(["git", "remote", "add", "origin", remote], check=False)
            return True
        except Exception as e:
            self.logger.error(f"Failed to init git at {path}: {e}")
            return False

    def write_gitignore(self, path: Union[str, Path], extras: Optional[List[str]] = None) -> None:
        """
        Write a .gitignore with standard Python/IDE entries and any extras provided.
        """
        path = Path(path) / ".gitignore"
        defaults = [
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            "*.so",
            ".env",
            ".venv/",
            "env/",
            "venv/",
            "dist/",
            "build/",
            "pip-wheel-metadata/",
            ".pytest_cache/",
            ".mypy_cache/",
            ".vscode/",
            ".idea/",
            "*.egg-info/",
            ".DS_Store",
        ]
        if extras:
            defaults.extend(extras)
        try:
            self.logger.info(f"Writing .gitignore at {path}")
            if not self.dry_run:
                path.write_text("\n".join(defaults) + "\n", encoding="utf-8")
        except Exception as e:
            self.logger.warn(f"Could not write .gitignore: {e}")

    def setup_precommit(self, path: Union[str, Path], auto_install: bool = False) -> None:
        """
        Write a basic .pre-commit-config.yaml and optionally run 'pre-commit install'.
        This is non-fatal if pre-commit isn't available.
        """
        path = Path(path)
        config_path = path / ".pre-commit-config.yaml"
        config_content = """repos:
-   repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
    - id: black
-   repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
    - id: isort
-   repo: https://gitlab.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    - id: flake8
"""
        try:
            self.logger.info(f"Writing pre-commit config at {config_path}")
            if not self.dry_run:
                config_path.write_text(config_content, encoding="utf-8")
            if auto_install:
                if shutil.which("pre-commit") is None:
                    self.logger.warn("pre-commit not installed; skipping auto install. You can install via 'pip install pre-commit'.")
                else:
                    self.logger.info("Installing pre-commit hooks")
                    self.runner.run(["pre-commit", "install"], check=True)
        except Exception as e:
            self.logger.warn(f"Pre-commit setup failed: {e}")

    def write_github_actions_ci(self, path: Union[str, Path], python_version: str = "3.11") -> None:
        """
        Write a simple GitHub Actions workflow file for running tests.
        """
        path = Path(path) / ".github" / "workflows"
        workflow_path = path / "ci.yml"
        workflow_content = f"""name: CI

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '{python_version}'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest -q
"""
        try:
            self.logger.info(f"Writing GitHub Actions workflow to {workflow_path}")
            if not self.dry_run:
                path.mkdir(parents=True, exist_ok=True)
                workflow_path.write_text(workflow_content, encoding="utf-8")
        except Exception as e:
            self.logger.warn(f"Could not write GitHub Actions workflow: {e}")

# -----------------------
# Project scaffolding & IDE integration
# -----------------------


class ProjectScaffolder:
    """
    Create a standard Python project layout and sample files for tests/docs.
    """

    def __init__(self, logger: SetupLogger, dry_run: bool = False) -> None:
        self.logger = logger
        self.dry_run = dry_run

    def scaffold(self, root: Union[str, Path], package_name: Optional[str] = None, author: Optional[str] = None) -> None:
        """
        Create folders: src/{package_name}, tests, docs, notebooks, data.
        Add sample module, __init__.py, basic pytest test, and requirements stubs.
        """
        root = Path(root)
        package_name = package_name or root.name.replace("-", "_")
        self.logger.info(f"Scaffolding project at {root} with package '{package_name}'")

        dirs = [
            root / "src" / package_name,
            root / "tests",
            root / "docs",
            root / "notebooks",
            root / "data",
        ]
        for d in dirs:
            if not self.dry_run:
                d.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {d}")

        files_to_create = {
            root / "src" / package_name / "__init__.py": f'"""Package {package_name}"""',
            root / "src" / package_name / "utils.py": '"""Utility functions for the package."""\n\n\ndef add(a, b):\n    """Return a + b."""\n    return a + b\n',
            root / "tests" / "test_utils.py": f"from {package_name}.utils import add\n\n\ndef test_add():\n    assert add(2, 2) == 4\n",
            root / "tests" / "conftest.py": "import sys, pathlib\n\n# Ensure 'src' is on sys.path for imports in tests\nROOT = pathlib.Path(__file__).resolve().parents[1]\nSRC = ROOT / 'src'\nif str(SRC) not in sys.path:\n    sys.path.insert(0, str(SRC))\n",
            root / "README.md": f"# {package_name}\n\nAuthor: {author or 'author'}\n",
            root / "docs" / "index.md": f"# Documentation for {package_name}\n",
            root / "requirements.txt": "# runtime dependencies\n",
            root / "requirements-dev.txt": "# dev dependencies\n",
            root / "pyproject.toml": f'[project]\nname = "{package_name}"\nversion = "0.1.0"\nauthors = [{{ name = "{author or 'author'}" }}]\ndescription = "A sample project."\nrequires-python = ">=3.8"\n\n[build-system]\nrequires = ["setuptools>=61.0"]\nbuild-backend = "setuptools.build_meta"\n',
        }

        for path, content in files_to_create.items():
            self._write_file(path, content)

    def _write_file(self, path: Path, content: str) -> None:
        try:
            if not self.dry_run:
                path.write_text(content, encoding="utf-8")
            self.logger.info(f"Wrote file: {path}")
        except Exception as e:
            self.logger.warn(f"Failed to write file {path}: {e}")


class IDEManager:
    """
    Provide basic IDE configuration for VS Code and PyCharm (guidance / files).
    """

    def __init__(self, logger: SetupLogger, dry_run: bool = False) -> None:
        self.logger = logger
        self.dry_run = dry_run

    def setup_vscode(self, root: Union[str, Path], venv_path: Optional[Union[str, Path]] = None) -> None:
        """
        Write .vscode/settings.json and extensions.json with helpful defaults.
        """
        root = Path(root) / ".vscode"
        settings = {
            "python.defaultInterpreterPath": str(venv_path / "bin" / "python") if venv_path and venv_path.exists() else "",
            "python.linting.enabled": True,
            "python.linting.pylintEnabled": False,
            "python.linting.flake8Enabled": True,
            "python.formatting.provider": "black",
            "editor.formatOnSave": True,
            "editor.codeActionsOnSave": {"source.organizeImports": True},
            "python.testing.pytestEnabled": True,
            "python.testing.pytestArgs": ["tests"],
        }
        extensions = {
            "recommendations": [
                "ms-python.python",
                "ms-python.vscode-pylance",
                "ms-azuretools.vscode-docker",
                "eamodio.gitlens",
                "njpwerner.autodocstring",
                "charliermarsh.ruff",
            ]
        }
        try:
            self.logger.info("Writing VS Code settings and recommended extensions")
            if not self.dry_run:
                root.mkdir(parents=True, exist_ok=True)
                (root / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
                (root / "extensions.json").write_text(json.dumps(extensions, indent=2), encoding="utf-8")
        except Exception as e:
            self.logger.warn(f"Failed to write VS Code config: {e}")

    def setup_pycharm_guidance(self, root: Union[str, Path]) -> None:
        """
        Write a simple Pycharm-README explaining interpreter setup (non-invasive).
        """
        root = Path(root)
        try:
            content = """PyCharm setup guidance:
1) Open this folder as project
2) Add interpreter: point to .venv or conda env interpreter
3) Recommended plugins: Docker, AWS Toolkit (if needed)
"""
            self.logger.info("Writing PyCharm guidance file")
            if not self.dry_run:
                (root / "Pycharm-README.md").write_text(content, encoding="utf-8")
        except Exception as e:
            self.logger.warn(f"Failed to write PyCharm guidance: {e}")

# -----------------------
# Setup orchestrator
# -----------------------


@dataclass
class OrchestratorResult:
    """Hold results for summary reporting."""
    start_time: float
    end_time: float
    profile: str
    env_type: str
    env_name_or_path: Optional[str]
    installed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class SetupOrchestrator:
    """
    Coordinates the full setup process by orchestrating other classes.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        """
        Initialize orchestrator and dependent components.

        Important: instantiate logger early to record actions from all components.
        """
        # Initialize logger
        log_file = args.log or DEFAULT_LOG_FILE
        self.logger = SetupLogger(log_path=log_file, verbose=args.verbose)
        # Subprocess runner with dry-run awareness and configured timeout
        self.runner = SubprocessRunner(self.logger, dry_run=args.dry_run, timeout=args.timeout or DEFAULT_TIMEOUT)
        # System detection
        self.sysdetector = SystemDetector(self.logger, self.runner)
        self.sysinfo = self.sysdetector.detect()
        # Config manager
        self.config = ConfigManager(self.logger)
        # UI
        self.ui = UserInterface(self.logger)
        # Managers
        self.env_manager = EnvironmentManager(self.logger, self.runner, dry_run=args.dry_run)
        self.package_resolver = PackageResolver(self.logger, self.config, self.sysinfo)
        self.package_installer = PackageInstaller(self.logger, self.runner, self.env_manager, dry_run=args.dry_run)
        self.git_manager = GitManager(self.logger, self.runner, dry_run=args.dry_run)
        self.scaffolder = ProjectScaffolder(self.logger, dry_run=args.dry_run)
        self.ide_manager = IDEManager(self.logger, dry_run=args.dry_run)

        # CLI args captured
        self.args = args

    def run(self) -> int:
        """
        Main execution entry. Returns exit code (0 success, >0 error).
        """
        start_time = time.time()
        profile_name = self.args.profile or self.ui.choose_profile(
            default="standard_ds", profiles=self.config.PROFILES, non_interactive=self.args.non_interactive
        )

        custom_packages: List[str] = []
        if profile_name == "custom":
            if self.args.packages:
                custom_packages = [p.strip() for p in self.args.packages.split(",") if p.strip()]
            elif not self.args.non_interactive:
                resp = self.ui.prompt_text("Enter comma-separated pip packages:", default="")
                if resp:
                    custom_packages = [p.strip() for p in resp.split(",") if p.strip()]

        self.ui.show_system_info(self.sysinfo)
        self._validate_prereqs()

        env_choice = self.args.env or self._auto_env_choice(profile_name)
        self.logger.info(f"Selected environment manager: {env_choice}")

        project_root = Path.cwd()
        env_name = self.args.env_name or f"{project_root.name}-{profile_name}"
        venv_path = project_root / ".venv"

        if not self.args.force and not self.args.non_interactive and not self.args.dry_run:
            if not self.ui.confirm(f"Proceed with creating environment '{env_name}' using {env_choice}?", default=True):
                self.logger.info("User cancelled operation.")
                return 0

        env_path: Optional[Path] = None
        if env_choice == "conda":
            if self.env_manager.create_conda_env(env_name, python_version=self.config.PROFILES.get(profile_name, {}).get("python")):
                self.logger.info(f"Conda env '{env_name}' created or confirmed.")
        elif env_choice == "venv":
            if self.env_manager.create_venv(venv_path):
                self.logger.info(f"venv created at '{venv_path}'")
                env_path = venv_path

        resolved = self.package_resolver.resolve(profile_name, custom_packages=custom_packages)
        packages = resolved.get("packages", [])
        dev_packages = resolved.get("dev_packages", [])

        if self.args.dry_run:
            self.ui.final_summary({
                "profile": profile_name,
                "env_choice": env_choice,
                "env_name": str(env_name if env_choice == "conda" else venv_path),
                "packages": packages,
                "dev_packages": dev_packages,
                "notes": self._collect_hardware_notes(),
            })
            self.logger.info("Dry-run complete. No changes applied.")
            return 0

        installed_packages, failed_packages = self._install_packages(env_choice, env_name, venv_path, packages, dev_packages)

        self.scaffolder.scaffold(project_root, package_name=self.args.package_name, author=self.args.author)

        if self.args.init_git:
            self.git_manager.init_repo(project_root, remote=self.args.remote)
            self.git_manager.write_gitignore(project_root)
            self.git_manager.setup_precommit(project_root, auto_install=not self.args.non_interactive)

        if self.args.ci:
            self.git_manager.write_github_actions_ci(project_root, python_version=self.config.PROFILES.get(profile_name, {}).get("python") or self.sysinfo.python_version)

        if self.args.vscode:
            self.ide_manager.setup_vscode(project_root, venv_path=env_path)

        if self.args.pycharm:
            self.ide_manager.setup_pycharm_guidance(project_root)

        result = OrchestratorResult(
            start_time=start_time,
            end_time=time.time(),
            profile=profile_name,
            env_type=env_choice,
            env_name_or_path=str(env_name if env_choice == "conda" else venv_path),
            installed=installed_packages,
            failed=failed_packages,
            notes=self._collect_hardware_notes(),
        )

        self._write_summary(result)

        if failed_packages:
            self.logger.warn(f"Setup completed with failures: {failed_packages}")
            return 2

        self.logger.info("Setup completed successfully.")
        return 0

    def _install_packages(
        self, env_choice: str, env_name: str, venv_path: Path, packages: List[str], dev_packages: List[str]
    ) -> Tuple[List[str], List[str]]:
        installed: List[str] = []
        failed: List[str] = []

        if env_choice == "conda":
            conda_candidates, pip_candidates = self._split_conda_candidates(packages)
            if conda_candidates:
                success, fails = self.package_installer.install_packages_conda(env_name, conda_candidates, channels=["conda-forge"])
                installed.extend(p for p in conda_candidates if p not in fails)
                failed.extend(fails)
            if pip_candidates:
                success, fails = self.package_installer.install_packages_pip(env_name, pip_candidates)
                installed.extend(p for p in pip_candidates if p not in fails)
                failed.extend(fails)
            if dev_packages:
                success, fails = self.package_installer.install_packages_pip(env_name, dev_packages)
                installed.extend(p for p in dev_packages if p not in fails)
                failed.extend(fails)
        elif env_choice == "venv":
            success, fails = self.package_installer.install_packages_pip(str(venv_path), packages, venv_path=venv_path)
            installed.extend(p for p in packages if p not in fails)
            failed.extend(fails)
            if dev_packages:
                success, fails = self.package_installer.install_packages_pip(str(venv_path), dev_packages, venv_path=venv_path)
                installed.extend(p for p in dev_packages if p not in fails)
                failed.extend(fails)
        else:  # system
            success, fails = self.package_installer.install_packages_pip("system", packages)
            installed.extend(p for p in packages if p not in fails)
            failed.extend(fails)
            if dev_packages:
                success, fails = self.package_installer.install_packages_pip("system", dev_packages)
                installed.extend(p for p in dev_packages if p not in fails)
                failed.extend(fails)

        return installed, failed

    def _write_summary(self, result: OrchestratorResult) -> None:
        summary = self._format_summary(result)
        try:
            Path(SUMMARY_FILE).write_text(json.dumps(summary, indent=2), encoding="utf-8")
            self.logger.info(f"Wrote summary to {SUMMARY_FILE}")
        except Exception as e:
            self.logger.warn(f"Could not write summary: {e}")
        self.ui.final_summary(summary)

    # -----------------------
    # Helper methods
    # -----------------------

    def _auto_env_choice(self, profile: str) -> str:
        """
        Select environment manager automatically based on system detection and profile.
        Prefer conda on Apple Silicon and if GPU heavy profile is used.
        """
        if self.args.env:
            return self.args.env
        if self.sysinfo.has_apple_silicon:
            return "conda"
        if profile in ("deep_learning", "cloud_ml") and self.sysinfo.has_nvidia:
            return "conda"
        # default to venv for lighter weight setups
        return "venv"

    def _validate_prereqs(self) -> None:
        """
        Run non-invasive checks and log recommendations. Do not change system state here.
        """
        self.logger.info("Validating prerequisites (non-invasive checks)...")
        # Python version check
        try:
            major, minor, *_ = [int(x) for x in platform.python_version_tuple()]
            if (major, minor) < (3, 8):
                self.logger.warn("Python < 3.8 detected - recommend upgrading to 3.8 or later.")
            else:
                self.logger.debug(f"Python version is sufficient: {platform.python_version()}")
        except Exception:
            self.logger.debug("Unable to parse Python version.")

        # Disk space
        if self.sysinfo.free_disk_gb < 5.0:
            self.logger.warn(f"Low free disk space: {self.sysinfo.free_disk_gb:.2f} GB. Installs may fail.")
        # RAM
        if self.sysinfo.total_ram_gb < 4.0:
            self.logger.warn(f"Low RAM: {self.sysinfo.total_ram_gb:.2f} GB. Consider using minimal profile or cloud resources.")

        # Internet connectivity check to pypi via DNS/ping (best-effort)
        try:
            if shutil.which("ping"):
                self.runner.run(["ping", "-c", "1", "pypi.org"], check=False)
            else:
                self.logger.debug("Ping utility not available for quick internet check.")
        except Exception:
            self.logger.debug("Ping check failed or was skipped.")

    def _split_conda_candidates(self, packages: List[str]) -> Tuple[List[str], List[str]]:
        """
        Heuristic: choose packages better installed via conda. Return (conda_candidates, pip_candidates).
        """
        conda_like = {"torch", "tensorflow", "tensorflow-cpu", "pytorch", "cudatoolkit", "cuda", "cupy", "opencv", "scikit-learn", "pillow"}
        conda_candidates = []
        pip_candidates = []
        for p in packages:
            name = p.split("==")[0].lower()
            if any(x in name for x in conda_like):
                conda_candidates.append(p)
            else:
                pip_candidates.append(p)
        self.logger.debug(f"conda_candidates={conda_candidates}, pip_candidates={pip_candidates}")
        return conda_candidates, pip_candidates

    def _collect_hardware_notes(self) -> List[str]:
        """Assemble a list of helpful hardware-related notes for the user."""
        notes = []
        if self.sysinfo.has_apple_silicon:
            notes.append(self.config.HARDWARE_RULES.get("apple_silicon", {}).get("hint", ""))
        if self.sysinfo.has_nvidia:
            notes.append(self.config.HARDWARE_RULES.get("nvidia_cuda", {}).get("hint", ""))
        if self.sysinfo.total_ram_gb < 8.0:
            notes.append(self.config.HARDWARE_RULES.get("low_ram", {}).get("hint", ""))
        # Remove empties
        return [n for n in notes if n]

    def _format_summary(self, result: OrchestratorResult) -> Dict[str, Any]:
        """Convert result dataclass to JSON-serializable dict for user and audit logs."""
        duration = result.end_time - result.start_time
        return {
            "profile": result.profile,
            "environment": {
                "type": result.env_type,
                "name_or_path": result.env_name_or_path,
            },
            "duration_seconds": round(duration, 2),
            "installed_packages": result.installed,
            "failed_packages": result.failed,
            "notes": result.notes,
            "system": {
                "os": f"{self.sysinfo.os_name} {self.sysinfo.os_version}",
                "machine": self.sysinfo.machine,
                "python": self.sysinfo.python_version,
            },
        }

# -----------------------
# CLI parsing
# -----------------------

def build_argparser() -> argparse.ArgumentParser:
    """
    Build and return the argparse parser for the script.
    """
    parser = argparse.ArgumentParser(description="Best-practice profile-driven AI & Data Science environment setup tool (refactored)")
    parser.add_argument("--profile", "-p", type=str, choices=list(ConfigManager.PROFILES.keys()), help="Profile to use")
    parser.add_argument("--non-interactive", action="store_true", help="Run without interactive prompts (use sensible defaults)")
    parser.add_argument("--env", choices=["conda", "venv", "system"], help="Which environment manager to use (override auto selection)")
    parser.add_argument("--env-name", type=str, help="Name used for environment (conda) or prefix for venv naming")
    parser.add_argument("--init-git", action="store_true", help="Initialize a git repository and set up pre-commit")
    parser.add_argument("--remote", type=str, help="Optional git remote URL to add as origin")
    parser.add_argument("--ci", action="store_true", help="Generate a GitHub Actions CI workflow")
    parser.add_argument("--vscode", action="store_true", help="Create VS Code settings and recommended extensions")
    parser.add_argument("--pycharm", action="store_true", help="Write PyCharm guidance file")
    parser.add_argument("--packages", type=str, help="Comma-separated package names when using custom profile (--profile custom)")
    parser.add_argument("--package-name", type=str, help="Package name to create under src/ (default uses project dir name)")
    parser.add_argument("--author", type=str, help="Author name used in sample files")
    parser.add_argument("--timeout", type=int, help="Timeout seconds for subprocess operations", default=DEFAULT_TIMEOUT)
    parser.add_argument("--log", type=str, help="Path to log file", default=DEFAULT_LOG_FILE)
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without making changes")
    parser.add_argument("--validate", action="store_true", help="Run validations only (no changes). Useful for CI.")
    parser.add_argument("--force", action="store_true", help="Skip confirmations and force actions")
    return parser


def main() -> None:
    """
    Program entry point: parse CLI args, create orchestrator, and run.
    """
    parser = build_argparser()
    args = parser.parse_args()

    orchestrator = SetupOrchestrator(args)

    if args.validate:
        orchestrator._validate_prereqs()
        orchestrator.logger.info("Validation-only run complete.")
        sys.exit(0)

    try:
        rc = orchestrator.run()
        sys.exit(rc)
    except KeyboardInterrupt:
        orchestrator.logger.warn("Interrupted by user (KeyboardInterrupt). Exiting.")
        sys.exit(130)
    except Exception as ex:
        orchestrator.logger.error(f"Unexpected error: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    main()
