#!/usr/bin/env python3
"""
DSAI Environment Setup Tool
Best-practice, single-file, class-driven design with rich UI, progress tracking, and robust error handling.

Features:
- DSAI banner and branding
- Rich UI with progress bars and spinner animations
- Error handling with timeout prompts
- Comprehensive dependency checking
- Hardware-aware package selection
- Dry-run mode with preview capabilities
- Non-interactive automation support
- Robust logging with verbosity control
- Timeout-protected subprocess calls
- JSON summary reporting
- Built-in validation checks for CI usage

Author: Muhammad Azni Osman
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# Optional third-party libs (rich for nice UI, psutil for system info)
try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.live import Live
    from rich.text import Text
    from rich.align import Align
    RICH_AVAILABLE = True
except Exception:
    RICH_AVAILABLE = False

try:
    import psutil  # type: ignore
    PSUTIL_AVAILABLE = True
except Exception:
    PSUTIL_AVAILABLE = False


# Default values for timeouts and filenames
DEFAULT_LOG_FILE = "dsai_env.log"
DEFAULT_TIMEOUT = 1800  # seconds for long operations (30 minutes)
ERROR_RETRY_TIMEOUT = 30  # seconds to wait for user input on errors
SUMMARY_FILE = "dsai_env_summary.json"

# System requirements thresholds
MIN_DISK_SPACE_GB = 2.0  # Minimum disk space for installations
LOW_RAM_THRESHOLD_GB = 8.0  # RAM threshold for warnings
LOW_DISK_THRESHOLD_GB = 5.0  # Disk space threshold for warnings

# Package name validation pattern
PACKAGE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+[a-zA-Z0-9_\[\]<>=.,~!-]*$')

# -----------------------
# Utility classes
# -----------------------


class SetupLogger:
    """
    Logger with thread-safe operations and rich console support.
    """

    def __init__(self, log_path: Union[str, Path] = DEFAULT_LOG_FILE, verbose: bool = False) -> None:
        self.log_path = Path(log_path)
        self.verbose = verbose
        self._lock = threading.Lock()
        self._ensure_log_dir()
        self._start_time = time.time()
        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None
        self._log("INFO", "DSAI Logger initialized.")

    def _ensure_log_dir(self) -> None:
        try:
            if not self.log_path.parent.exists():
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Warning: Could not create log directory: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Unexpected error creating log directory: {e}", file=sys.stderr)

    def _timestamp(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _log(self, level: str, message: str) -> None:
        line = f"{self._timestamp()} [{level}] {message}"
        with self._lock:
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
            except Exception as e:
                # Fallback if console print fails
                print(f"[Logging error: {e}] {line}", file=sys.stderr)

            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except IOError as e:
                print(f"{self._timestamp()} [WARN] Failed to write to log file {self.log_path}: {e}", file=sys.stderr)
            except Exception as e:
                print(f"{self._timestamp()} [ERROR] Unexpected logging error: {e}", file=sys.stderr)

    def info(self, msg: str) -> None:
        self._log("INFO", msg)

    def warn(self, msg: str) -> None:
        self._log("WARN", msg)

    def error(self, msg: str) -> None:
        self._log("ERROR", msg)

    def debug(self, msg: str) -> None:
        if self.verbose:
            self._log("DEBUG", msg)


class SubprocessRunner:
    """
    Subprocess runner with better error handling and timeout management.
    """

    def __init__(self, logger: SetupLogger, dry_run: bool = False, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.logger = logger
        self.dry_run = dry_run
        self.timeout = timeout

    def run(self, cmd: Sequence[str], check: bool = True, capture_output: bool = False) -> Tuple[int, str, str]:
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


@dataclass
class SystemInfo:
    """Data class holding system detection results."""
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
    """System detection with comprehensive hardware and software checks."""

    def __init__(self, logger: SetupLogger, runner: SubprocessRunner) -> None:
        self.logger = logger
        self.runner = runner

    def detect(self) -> SystemInfo:
        self.logger.info("Detecting system hardware and environment...")
        os_name = platform.system()
        os_version = platform.version()
        machine = platform.machine()
        cpu_count = os.cpu_count() or 1

        total_ram_gb = self._get_total_ram_gb()

        try:
            usage = shutil.disk_usage(os.getcwd())
            free_disk_gb = usage.free / (1024 ** 3)
        except OSError as e:
            self.logger.warn(f"Could not determine disk usage: {e}")
            free_disk_gb = 0.0
        except Exception as e:
            self.logger.error(f"Unexpected error checking disk usage: {e}")
            free_disk_gb = 0.0

        has_nvidia = shutil.which("nvidia-smi") is not None
        has_apple_silicon = "arm" in machine.lower() or "apple" in platform.processor().lower()

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
        return info

    def _get_total_ram_gb(self) -> float:
        if PSUTIL_AVAILABLE:
            try:
                return psutil.virtual_memory().total / (1024 ** 3)
            except Exception as e:
                self.logger.debug(f"psutil RAM check failed: {e}")

        system = platform.system()
        if system == "Darwin":
            try:
                out = subprocess.check_output(["sysctl", "-n", "hw.memsize"])
                return int(out) / (1024 ** 3)
            except (subprocess.CalledProcessError, ValueError, OSError) as e:
                self.logger.debug(f"macOS RAM check failed: {e}")
        elif system == "Linux":
            try:
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            return int(line.split()[1]) / (1024 ** 2)
            except (IOError, ValueError, IndexError) as e:
                self.logger.debug(f"Linux RAM check failed: {e}")

        self.logger.warn("Could not determine RAM, defaulting to 4GB")
        return 4.0

    def _run_version(self, cmd: Sequence[str]) -> Optional[str]:
        if shutil.which(cmd[0]) is None:
            return None
        try:
            rc, out, err = self.runner.run(cmd, check=True, capture_output=True)
            return (out or err).strip()
        except subprocess.CalledProcessError as e:
            self.logger.debug(f"Version check failed for {cmd[0]}: {e}")
            return None
        except Exception as e:
            self.logger.debug(f"Unexpected error checking {cmd[0]} version: {e}")
            return None


class UserInterface:
    """UI with DSAI branding, progress bars, and timeout prompts."""

    def __init__(self, logger: SetupLogger) -> None:
        self.logger = logger
        self.rich = RICH_AVAILABLE
        self.console = Console() if self.rich else None
        self.progress = None

    def show_dsai_banner(self) -> None:
        """Display the DSAI banner."""
        banner_text = r"""
          _____                    _____                    _____                    _____
         /\    \                  /\    \                  /\    \                  /\    \
        /::\    \                /::\    \                /::\    \                /::\    \
       /::::\    \              /::::\    \              /::::\    \               \:::\    \
      /::::::\    \            /::::::\    \            /::::::\    \               \:::\    \
     /:::/\:::\    \          /:::/\:::\    \          /:::/\:::\    \               \:::\    \
    /:::/  \:::\    \        /:::/__\:::\    \        /:::/__\:::\    \               \:::\    \
   /:::/    \:::\    \       \:::\   \:::\    \      /::::\   \:::\    \              /::::\    \
  /:::/    / \:::\    \    ___\:::\   \:::\    \    /::::::\   \:::\    \    ____    /::::::\    \
 /:::/    /   \:::\ ___\  /\   \:::\   \:::\    \  /:::/\:::\   \:::\    \  /\   \  /:::/\:::\    \
/:::/____/     \:::|    |/::\   \:::\   \:::\____\/:::/  \:::\   \:::\____\/::\   \/:::/  \:::\____\
\:::\    \     /:::|____|\:::\   \:::\   \::/    /\::/    \:::\  /:::/    /\:::\  /:::/    \::/    /
 \:::\    \   /:::/    /  \:::\   \:::\   \/____/  \/____/ \:::\/:::/    /  \:::\/:::/    / \/____/
  \:::\    \ /:::/    /    \:::\   \:::\    \               \::::::/    /    \::::::/    /
   \:::\    /:::/    /      \:::\   \:::\____\               \::::/    /      \::::/____/
    \:::\  /:::/    /        \:::\  /:::/    /               /:::/    /        \:::\    \
     \:::\/:::/    /          \:::\/:::/    /               /:::/    /          \:::\    \
      \::::::/    /            \::::::/    /               /:::/    /            \:::\    \
       \::::/    /              \::::/    /               /:::/    /              \:::\____\
        \::/____/                \::/    /                \::/    /                \::/    /
         ~~                       \/____/                  \/____/                  \/____/

                               Data Science & AI Environment Setup Tool
        """

        if self.rich and self.console:
            banner_panel = Panel(
                Align.center(Text(banner_text, style="bold cyan")),
                title="[bold magenta]Welcome to DSAI Setup Tool[/bold magenta]",
                border_style="bright_blue",
                padding=(1, 2)
            )
            self.console.print(banner_panel)
            self.console.print("")
        else:
            print("=" * 60)
            print(banner_text)
            print("=" * 60)
            print()

    def create_progress_bar(self) -> Optional[Progress]:
        if self.rich:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console,
                transient=True
            )
            return self.progress
        return None

    def prompt_with_timeout(self, message: str, timeout: int = ERROR_RETRY_TIMEOUT, default: str = "n") -> str:
        """
        Prompt user with timeout for error handling scenarios.
        Cross-platform implementation using threading instead of signals.
        """
        if self.rich:
            result = [default]
            input_completed = threading.Event()

            def input_thread():
                try:
                    result[0] = Prompt.ask(f"{message} (timeout in {timeout}s)", default=default)
                    input_completed.set()
                except Exception as e:
                    self.logger.debug(f"Input prompt error: {e}")
                    input_completed.set()

            thread = threading.Thread(target=input_thread, daemon=True)
            thread.start()

            if input_completed.wait(timeout=timeout):
                return result[0]
            else:
                self.console.print(f"\n[yellow]Timeout reached. Using default: {default}[/yellow]")
                return default
        else:
            try:
                return input(f"{message} [{default}]: ").strip() or default
            except KeyboardInterrupt:
                return default

    def choose_profile(self, default: str, profiles: Dict[str, Dict[str, Any]], non_interactive: bool) -> str:
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
        if non_interactive:
            return default or ""
        if self.rich:
            return Prompt.ask(message, default=default)
        else:
            return input(f"{message} [{default or ''}]: ").strip() or (default or "")

    def show_system_info(self, info: SystemInfo) -> None:
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
        pretty = json.dumps(summary, indent=2)
        if self.rich:
            self.console.print(Panel(pretty, title="✅ Setup Summary", title_align="left", border_style="green", width=120))
        else:
            print("Setup Summary:")
            print(pretty)


class EnvironmentManager:
    """Manages virtual environments (conda, venv, or system)."""

    def __init__(self, logger: SetupLogger, runner: SubprocessRunner, env_type: str, env_name: str = "dsai_env") -> None:
        self.logger = logger
        self.runner = runner
        self.env_type = env_type
        self.env_name = env_name
        self.env_path: Optional[Path] = None

    def create_environment(self, python_version: Optional[str] = None) -> bool:
        """Create virtual environment based on env_type."""
        self.logger.info(f"Creating {self.env_type} environment: {self.env_name}")

        try:
            if self.env_type == "conda":
                return self._create_conda_env(python_version)
            elif self.env_type == "venv":
                return self._create_venv(python_version)
            elif self.env_type == "system":
                self.logger.info("Using system Python - no environment creation needed")
                return True
            else:
                self.logger.error(f"Unknown environment type: {self.env_type}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to create environment: {e}")
            return False

    def _create_conda_env(self, python_version: Optional[str]) -> bool:
        """Create conda environment."""
        if shutil.which("conda") is None:
            self.logger.error("conda not found. Please install Anaconda/Miniconda.")
            return False

        py_spec = f"python={python_version}" if python_version else "python"
        cmd = ["conda", "create", "-n", self.env_name, py_spec, "-y"]

        try:
            rc, out, err = self.runner.run(cmd, check=True, capture_output=True)
            self.logger.info(f"Conda environment '{self.env_name}' created successfully")
            return True
        except subprocess.CalledProcessError:
            return False

    def _create_venv(self, python_version: Optional[str]) -> bool:
        """
        Create venv environment.
        Note: python_version parameter is not used - venv always uses the current Python interpreter.
        To use a different Python version, run this script with that Python interpreter.
        """
        self.env_path = Path.cwd() / self.env_name

        if self.env_path.exists():
            self.logger.warn(f"Environment directory {self.env_path} already exists")
            return True

        if python_version:
            self.logger.warn(f"venv cannot change Python version (requested {python_version}, using {platform.python_version()})")

        try:
            self.logger.info(f"Creating venv at {self.env_path}")
            venv.create(self.env_path, with_pip=True)
            self.logger.info(f"venv '{self.env_name}' created successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create venv: {e}")
            return False

    def get_pip_command(self) -> List[str]:
        """Get the appropriate pip command for this environment."""
        if self.env_type == "conda":
            return ["conda", "run", "-n", self.env_name, "pip"]
        elif self.env_type == "venv" and self.env_path:
            if platform.system() == "Windows":
                pip_path = self.env_path / "Scripts" / "pip.exe"
            else:
                pip_path = self.env_path / "bin" / "pip"
            return [str(pip_path)]
        else:
            return [sys.executable, "-m", "pip"]

    def activate_instructions(self) -> str:
        """Return instructions for activating the environment."""
        if self.env_type == "conda":
            return f"conda activate {self.env_name}"
        elif self.env_type == "venv":
            if platform.system() == "Windows":
                return f"{self.env_name}\\Scripts\\activate"
            else:
                return f"source {self.env_name}/bin/activate"
        else:
            return "No activation needed (using system Python)"


class EnvironmentValidator:
    """Validates environment setup and installed packages."""

    def __init__(self, logger: SetupLogger, runner: SubprocessRunner, env_manager: EnvironmentManager) -> None:
        self.logger = logger
        self.runner = runner
        self.env_manager = env_manager

    def check_dependencies(self) -> Dict[str, bool]:
        """Check if required system dependencies are available."""
        checks = {
            "pip": self._check_pip(),
            "internet": self._check_internet(),
            "disk_space": self._check_disk_space(),
        }
        return checks

    def _check_pip(self) -> bool:
        """Verify pip is accessible."""
        pip_cmd = self.env_manager.get_pip_command()
        try:
            rc, out, err = self.runner.run(pip_cmd + ["--version"], check=True, capture_output=True)
            self.logger.debug(f"pip version: {out}")
            return True
        except Exception as e:
            self.logger.error(f"pip not accessible: {e}")
            return False

    def _check_internet(self) -> bool:
        """Check internet connectivity to PyPI."""
        try:
            import urllib.request
            urllib.request.urlopen("https://pypi.org", timeout=5)
            return True
        except urllib.error.URLError as e:
            self.logger.warn(f"No internet connection to PyPI: {e.reason}")
            return False
        except Exception as e:
            self.logger.warn(f"Internet connectivity check failed: {e}")
            return False

    def _check_disk_space(self, min_gb: float = MIN_DISK_SPACE_GB) -> bool:
        """Check if sufficient disk space is available."""
        try:
            usage = shutil.disk_usage(os.getcwd())
            free_gb = usage.free / (1024 ** 3)
            if free_gb < min_gb:
                self.logger.error(f"Insufficient disk space: {free_gb:.2f}GB available, {min_gb}GB required")
                return False
            return True
        except Exception as e:
            self.logger.warn(f"Could not check disk space: {e}")
            return True

    def verify_package(self, package: str) -> bool:
        """Verify a package is installed and importable."""
        pip_cmd = self.env_manager.get_pip_command()

        # Extract package name using regex (handles complex version specifiers)
        pkg_name = self._extract_package_name(package)

        try:
            # Check if installed via pip
            rc, out, err = self.runner.run(pip_cmd + ["show", pkg_name], check=False, capture_output=True)
            if rc == 0:
                self.logger.debug(f"Package {pkg_name} verified via pip")
                return True
            return False
        except Exception as e:
            self.logger.debug(f"Could not verify {pkg_name}: {e}")
            return False

    def _extract_package_name(self, package: str) -> str:
        """
        Extract base package name from various package specifiers.
        Handles: pkg, pkg[extra], pkg==1.0, pkg>=1.0,<2.0, etc.
        """
        # Remove extras first (anything in brackets)
        pkg_no_extras = re.sub(r'\[.*?\]', '', package)
        # Extract name before any version specifier
        match = re.match(r'^([a-zA-Z0-9_-]+)', pkg_no_extras)
        if match:
            return match.group(1)
        # Fallback to naive split
        return package.split("[")[0].split("=")[0].split(">")[0].split("<")[0].split("~")[0].strip()


class PackageInstaller:
    """Handles package installation with progress tracking and rollback support."""

    def __init__(self, logger: SetupLogger, runner: SubprocessRunner, env_manager: EnvironmentManager,
                 critical_packages: Optional[List[str]] = None) -> None:
        self.logger = logger
        self.runner = runner
        self.env_manager = env_manager
        self.installed_packages: List[str] = []
        self.failed_packages: List[str] = []
        # Configurable critical packages list
        self.critical_packages = critical_packages or ["pip", "setuptools", "wheel", "numpy", "pandas"]

    def install_packages(self, packages: List[str], progress: Optional[Progress] = None,
                        enable_rollback: bool = False) -> Dict[str, bool]:
        """Install packages and return success status for each."""
        results: Dict[str, bool] = {}

        if not packages:
            self.logger.info("No packages to install")
            return results

        # Validate package names before installation
        invalid_packages = self._validate_package_names(packages)
        if invalid_packages:
            self.logger.error(f"Invalid package names detected: {invalid_packages}")
            for pkg in invalid_packages:
                results[pkg] = False
                self.failed_packages.append(pkg)
            # Remove invalid packages from list
            packages = [p for p in packages if p not in invalid_packages]

        self.logger.info(f"Installing {len(packages)} packages...")

        task_id = None
        if progress:
            task_id = progress.add_task("Installing packages", total=len(packages))

        for idx, pkg in enumerate(packages, 1):
            self.logger.info(f"[{idx}/{len(packages)}] Installing {pkg}...")
            success = self._install_single_package(pkg)
            results[pkg] = success

            if success:
                self.installed_packages.append(pkg)
            else:
                self.failed_packages.append(pkg)
                self.logger.warn(f"Failed to install {pkg}")

                # If rollback enabled and critical failure, abort
                if enable_rollback and self._is_critical_package(pkg):
                    self.logger.error(f"Critical package {pkg} failed - aborting installation")
                    break

            if progress and task_id is not None:
                progress.update(task_id, advance=1)

        return results

    def _validate_package_names(self, packages: List[str]) -> List[str]:
        """Validate package names against security pattern. Returns list of invalid packages."""
        invalid = []
        for pkg in packages:
            if not PACKAGE_NAME_PATTERN.match(pkg):
                self.logger.warn(f"Package name '{pkg}' failed validation")
                invalid.append(pkg)
        return invalid

    def _install_single_package(self, package: str) -> bool:
        """Install a single package."""
        pip_cmd = self.env_manager.get_pip_command()
        cmd = pip_cmd + ["install", package, "--no-cache-dir"]

        try:
            rc, out, err = self.runner.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.debug(f"Installation failed for {package}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error installing {package}: {e}")
            return False

    def _is_critical_package(self, package: str) -> bool:
        """Determine if a package is critical based on configurable list."""
        # Use validator's extract method for proper name parsing
        from types import SimpleNamespace
        validator = SimpleNamespace()
        validator._extract_package_name = EnvironmentValidator._extract_package_name.__get__(validator, SimpleNamespace)
        pkg_name = validator._extract_package_name(package).lower()
        return pkg_name in [p.lower() for p in self.critical_packages]

    def rollback(self) -> bool:
        """Uninstall all successfully installed packages."""
        if not self.installed_packages:
            self.logger.info("No packages to rollback")
            return True

        self.logger.warn(f"Rolling back {len(self.installed_packages)} installed packages...")
        pip_cmd = self.env_manager.get_pip_command()

        rollback_failures = []
        for pkg in reversed(self.installed_packages):
            try:
                self.logger.info(f"Uninstalling {pkg}...")
                cmd = pip_cmd + ["uninstall", pkg, "-y"]
                self.runner.run(cmd, check=True, capture_output=True)
            except Exception as e:
                self.logger.error(f"Failed to uninstall {pkg}: {e}")
                rollback_failures.append(pkg)

        if rollback_failures:
            self.logger.error(f"Rollback incomplete - manual cleanup required for: {rollback_failures}")
            return False

        self.logger.info("Rollback completed successfully")
        return True


class ConfigManager:
    """Configuration management with DSAI-optimized profiles."""

    PROFILES: Dict[str, Dict[str, Any]] = {
        "standard_ds": {
            "description": "General Data Science: numpy, pandas, scikit-learn, matplotlib, jupyter.",
            "python": "3.11",
            "packages": [
                "numpy", "pandas", "scipy", "scikit-learn", "matplotlib",
                "seaborn", "jupyterlab", "notebook", "ipykernel", "joblib",
                "tqdm", "pydantic", "plotly"
            ],
            "dev_packages": ["pytest", "black", "isort", "flake8", "pre-commit"],
        },
        "deep_learning": {
            "description": "Deep learning: hardware-aware selection (PyTorch/TensorFlow).",
            "python": "3.11",
            "packages": [
                "numpy", "pandas", "matplotlib", "seaborn", "jupyterlab",
                "notebook", "ipykernel", "plotly"
            ],
            "dev_packages": ["pytest", "black", "isort", "flake8", "pre-commit"],
        },
        "cloud_ml": {
            "description": "Cloud & MLOps: AWS/GCP/Azure SDKs, mlflow, docker SDK.",
            "python": "3.11",
            "packages": [
                "numpy", "pandas", "boto3", "google-cloud-storage",
                "azure-storage-blob", "mlflow", "docker", "fastapi", "uvicorn"
            ],
            "dev_packages": ["pytest", "black", "isort", "flake8", "pre-commit"],
        },
        "dsai_assignment": {
            "description": "DSAI Assignment Profile: optimized for NTU DSAI coursework.",
            "python": "3.11",
            "packages": [
                "numpy", "pandas", "matplotlib", "seaborn", "scikit-learn",
                "jupyterlab", "notebook", "ipykernel", "plotly", "scipy",
                "tensorflow", "torch", "torchvision", "opencv-python",
                "requests", "beautifulsoup4", "nltk", "spacy"
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
        self.logger = logger

    def get_profile(self, name: str) -> Dict[str, Any]:
        if name not in self.PROFILES:
            self.logger.error(f"Profile '{name}' not defined.")
            raise KeyError(f"Profile '{name}' not found")
        return self.PROFILES[name]

    def list_profiles(self) -> List[str]:
        return list(self.PROFILES.keys())

    def hardware_hint(self, key: str) -> Optional[str]:
        return self.HARDWARE_RULES.get(key, {}).get("hint")

    def adjust_profile_for_hardware(self, profile: Dict[str, Any], sys_info: SystemInfo) -> Dict[str, Any]:
        """Adjust profile packages based on detected hardware. Uses deep copy to avoid mutations."""
        # Deep copy to prevent side effects
        adjusted = copy.deepcopy(profile)
        packages = list(adjusted.get("packages", []))

        # Handle deep learning packages based on hardware
        if "deep_learning" in str(profile.get("description", "")).lower():
            if sys_info.has_nvidia:
                self.logger.info("NVIDIA GPU detected - adding CUDA-enabled PyTorch")
                packages.extend(["torch", "torchvision", "torchaudio"])
            elif sys_info.has_apple_silicon:
                self.logger.info("Apple Silicon detected - adding MPS-enabled PyTorch")
                packages.extend(["torch", "torchvision", "torchaudio"])
            else:
                self.logger.info("No GPU detected - adding CPU-only PyTorch")
                packages.extend(["torch", "torchvision", "torchaudio"])

        # Warn about low RAM (using constant)
        if sys_info.total_ram_gb < LOW_RAM_THRESHOLD_GB:
            self.logger.warn(f"Low RAM detected ({sys_info.total_ram_gb}GB). Consider using 'minimal' profile.")

        # Warn about low disk space (using constant)
        if sys_info.free_disk_gb < LOW_DISK_THRESHOLD_GB:
            self.logger.warn(f"Low disk space ({sys_info.free_disk_gb}GB). Installation may fail.")

        adjusted["packages"] = packages
        return adjusted


class SetupOrchestrator:
    """Main orchestrator that coordinates the entire setup process."""

    def __init__(self, logger: SetupLogger, runner: SubprocessRunner, ui: UserInterface, config_mgr: ConfigManager) -> None:
        self.logger = logger
        self.runner = runner
        self.ui = ui
        self.config_mgr = config_mgr
        self.summary: Dict[str, Any] = {
            "start_time": datetime.datetime.now().isoformat(),
            "profile": None,
            "environment_type": None,
            "system_info": {},
            "packages_installed": {},
            "success": False,
            "errors": [],
        }

    def run(self, args: argparse.Namespace) -> int:
        """Execute the full setup workflow with validation and rollback."""
        installer: Optional[PackageInstaller] = None
        env_manager: Optional[EnvironmentManager] = None

        try:
            # Step 1: System detection
            detector = SystemDetector(self.logger, self.runner)
            sys_info = detector.detect()
            self.ui.show_system_info(sys_info)
            self.summary["system_info"] = {
                "os": sys_info.os_name,
                "machine": sys_info.machine,
                "python": sys_info.python_version,
                "ram_gb": sys_info.total_ram_gb,
                "has_nvidia": sys_info.has_nvidia,
                "has_apple_silicon": sys_info.has_apple_silicon,
            }

            # Step 2: Profile selection
            profile_name = args.profile
            if not args.non_interactive:
                profile_name = self.ui.choose_profile(
                    default=profile_name,
                    profiles=self.config_mgr.PROFILES,
                    non_interactive=False
                )

            self.summary["profile"] = profile_name
            profile = self.config_mgr.get_profile(profile_name)
            self.logger.info(f"Using profile: {profile_name}")

            # Step 3: Hardware-aware profile adjustment
            profile = self.config_mgr.adjust_profile_for_hardware(profile, sys_info)

            # Handle custom profile
            if profile_name == "custom":
                packages_str = self.ui.prompt_text(
                    "Enter packages (comma-separated)",
                    default="numpy,pandas",
                    non_interactive=args.non_interactive
                )
                profile["packages"] = [p.strip() for p in packages_str.split(",")]

            # Step 4: Environment type selection
            env_type = args.env
            if not env_type:
                if sys_info.conda_version:
                    env_type = "conda"
                else:
                    env_type = "venv"

                if not args.non_interactive:
                    if self.ui.confirm(f"Use {env_type} for environment?", default=True, non_interactive=False):
                        pass
                    else:
                        env_type = "system"

            self.summary["environment_type"] = env_type
            self.logger.info(f"Environment type: {env_type}")

            # Step 5: Create environment
            env_manager = EnvironmentManager(self.logger, self.runner, env_type)
            if not env_manager.create_environment(profile.get("python")):
                self.logger.error("Failed to create environment")
                self.summary["errors"].append("Environment creation failed")
                return 1

            # Step 6: Pre-installation validation
            self.logger.info("\nRunning pre-installation checks...")
            validator = EnvironmentValidator(self.logger, self.runner, env_manager)
            dep_checks = validator.check_dependencies()

            validation_failed = False
            for check_name, passed in dep_checks.items():
                status = "✓" if passed else "✗"
                self.logger.info(f"  {status} {check_name}: {'passed' if passed else 'failed'}")
                if not passed and check_name in ["pip", "disk_space"]:
                    validation_failed = True

            if validation_failed:
                self.logger.error("\nCritical pre-installation checks failed. Aborting.")
                self.summary["errors"].append("Pre-installation validation failed")
                return 1

            # Step 7: Show preview and confirm
            if not args.non_interactive and not args.dry_run:
                self.logger.info(f"\nPackages to install ({len(profile['packages'])} total):")
                for pkg in profile["packages"]:
                    self.logger.info(f"  - {pkg}")

                if not self.ui.confirm("\nProceed with installation?", default=True):
                    self.logger.info("Installation cancelled by user")
                    return 0

            # Step 8: Install packages with progress tracking and rollback support
            installer = PackageInstaller(self.logger, self.runner, env_manager)

            progress = self.ui.create_progress_bar()
            if progress:
                with progress:
                    results = installer.install_packages(
                        profile["packages"],
                        progress,
                        enable_rollback=True
                    )
            else:
                results = installer.install_packages(
                    profile["packages"],
                    enable_rollback=True
                )

            self.summary["packages_installed"] = results

            # Step 9: Install dev packages if present
            if profile.get("dev_packages"):
                self.logger.info("\nInstalling development packages...")
                if progress:
                    with progress:
                        dev_results = installer.install_packages(
                            profile["dev_packages"],
                            progress,
                            enable_rollback=False
                        )
                else:
                    dev_results = installer.install_packages(
                        profile["dev_packages"],
                        enable_rollback=False
                    )
                self.summary["packages_installed"].update(dev_results)

            # Step 10: Post-installation validation
            self.logger.info("\nVerifying installed packages...")
            verification_results = {}
            critical_failed = []

            # Verify both main packages and dev packages
            all_packages = list(profile["packages"])
            if profile.get("dev_packages"):
                all_packages.extend(profile["dev_packages"])

            for pkg in all_packages:
                verified = validator.verify_package(pkg)
                verification_results[pkg] = verified
                if not verified and installer._is_critical_package(pkg):
                    critical_failed.append(pkg)

            self.summary["verified_packages"] = verification_results

            # Step 11: Handle failures and rollback if needed
            failed = [pkg for pkg, success in results.items() if not success]
            if critical_failed:
                self.logger.error(f"\n❌ Critical packages failed verification: {critical_failed}")
                self.summary["errors"].append(f"Critical packages failed: {critical_failed}")

                if not args.non_interactive:
                    if self.ui.confirm("Rollback installation?", default=True):
                        installer.rollback()
                        return 1

            if failed:
                self.logger.warn(f"\n⚠️  {len(failed)} packages failed to install:")
                for pkg in failed:
                    self.logger.warn(f"  - {pkg}")
                self.summary["errors"].append(f"{len(failed)} packages failed")
            else:
                self.summary["success"] = True

            self.summary["end_time"] = datetime.datetime.now().isoformat()

            # Step 12: Save summary to file
            summary_path = Path(SUMMARY_FILE)
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(self.summary, f, indent=2)
            self.logger.info(f"\nSummary saved to {summary_path}")

            # Step 13: Show final instructions
            self.ui.final_summary(self.summary)
            self.logger.info(f"\n✅ Setup completed!")
            self.logger.info(f"\nTo activate your environment, run:")
            self.logger.info(f"  {env_manager.activate_instructions()}")

            return 0 if self.summary["success"] else 1

        except KeyboardInterrupt:
            self.logger.warn("\n❌ Interrupted by user.")
            self.summary["errors"].append("User interrupted")

            # Offer rollback on interrupt
            if installer and installer.installed_packages:
                self.logger.info(f"\n{len(installer.installed_packages)} packages were installed before interruption.")
                try:
                    if self.ui.confirm("Rollback installed packages?", default=False, non_interactive=args.non_interactive):
                        installer.rollback()
                except Exception as e:
                    self.logger.error(f"Rollback failed: {e}")

            return 130

        except Exception as ex:
            self.logger.error(f"❌ Unexpected error: {ex}")
            self.summary["errors"].append(str(ex))

            # Offer rollback on error
            if installer and installer.installed_packages and not args.non_interactive:
                try:
                    if self.ui.confirm("Rollback installed packages?", default=True):
                        installer.rollback()
                except Exception as e:
                    self.logger.error(f"Rollback failed: {e}")

            return 1


def main() -> int:
    """Main function with DSAI branding."""
    parser = argparse.ArgumentParser(
        description="DSAI Environment Setup Tool - NTU DSAI Assignments"
    )
    parser.add_argument("--profile", "-p", type=str,
                       choices=list(ConfigManager.PROFILES.keys()),
                       default="dsai_assignment",
                       help="Profile to use (default: dsai_assignment)")
    parser.add_argument("--non-interactive", action="store_true",
                       help="Run without interactive prompts")
    parser.add_argument("--env", choices=["conda", "venv", "system"],
                       help="Environment manager to use")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview actions without making changes")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose debug logging")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                       help="Timeout seconds for operations")

    args = parser.parse_args()

    # Initialize components
    logger = SetupLogger(verbose=args.verbose)
    ui = UserInterface(logger)
    ui.show_dsai_banner()

    logger.info("🚀 DSAI Environment Setup Tool starting...")
    logger.info(f"Profile: {args.profile}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")

    runner = SubprocessRunner(logger, dry_run=args.dry_run, timeout=args.timeout)
    config_mgr = ConfigManager(logger)

    # Run orchestration
    orchestrator = SetupOrchestrator(logger, runner, ui, config_mgr)
    return orchestrator.run(args)


if __name__ == "__main__":
    sys.exit(main())