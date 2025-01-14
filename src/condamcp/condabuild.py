# condabuild.py 
"""
Conda build command wrapper that uses `commandlr` to build and execute conda build commands.
"""

import os
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime
import tempfile
from .commandlr import Commandlr
from .utils import get_default_conda_binary, get_conda_activation_commands

class CondaBuild(Commandlr):
    def __init__(self, *args, build_env=None, logs_dir=None, **kwargs):
        """Initialize conda build wrapper with default settings.
        
        Args:
            build_env: Name of conda environment containing conda-build (default: "build")
            logs_dir: Directory for build logs (default: system temp directory)
            *args, **kwargs: Arguments passed to Commandlr
        """
        super().__init__(*args, **kwargs)
        self.binary_path = get_default_conda_binary()
        self.build_env = build_env
        self.default_args = [
            "--no-anaconda-upload",
            "--error-overlinking"
        ]
        self.active_builds = {}
        
        # Use provided logs directory or create one in system temp
        if logs_dir:
            self.build_logs_dir = Path(logs_dir)
        else:
            temp_dir = Path(tempfile.gettempdir())
            self.build_logs_dir = temp_dir / "conda_build_logs"
        
        self.build_logs_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file(self, build_id):
        """Get the log file path for a build."""
        return self.build_logs_dir / f"build_{build_id}.log"

    def _run_build_process(self, build_id, command, log_file, env=None):
        """Run the build process and capture output to log file."""
        with open(log_file, 'w') as f:
            # Construct conda run command
            conda_command = [
                self.binary_path, "run",
                "-n", self.build_env,
                "--no-capture-output"
            ]
            
            # Add environment variables if specified
            if env:
                for key, value in env.items():
                    conda_command.extend(["-v", f"{key}={value}"])
            
            # Add "conda" before "build" since we're running conda-build inside the env
            conda_command.append("conda")
            conda_command.extend(command[1:])  # Skip the conda binary path from original command
            
            # Get the directory containing the config file from the command args
            config_dir = None
            for i, arg in enumerate(command):
                if arg == '--config-file':
                    config_dir = os.path.dirname(command[i + 1])
                    break
            
            process = subprocess.Popen(
                conda_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                env=os.environ.copy(),
                cwd=config_dir  # Set working directory to where config file is
            )
            
            self.active_builds[build_id] = {
                'process': process,
                'status': 'running',
                'start_time': datetime.now(),
                'log_file': log_file,
                'command': " ".join(conda_command)  # Store full command for debugging
            }

            # Stream output to log file
            for line in process.stdout:
                f.write(line)
                f.flush()

            returncode = process.wait()
            self.active_builds[build_id]['status'] = 'completed' if returncode == 0 else 'failed'
            self.active_builds[build_id]['end_time'] = datetime.now()

    def _validate_paths(self, recipe_path: str, config_file: str = None, croot: str = None) -> list[str]:
        """Validate that all required paths exist.

        Args:
            recipe_path: Path to recipe directory
            config_file: Path to conda build config file
            croot: Build root directory

        Returns:
            list: List of error messages, empty if all paths are valid
        """
        errors = []
        paths_to_check = {
            'Recipe': Path(recipe_path),
            'Config': Path(config_file) if config_file else None,
            'Build root': Path(croot) if croot else None
        }

        for name, path in paths_to_check.items():
            if path is not None and not path.exists():
                errors.append(f"{name} path does not exist: {path}")

        return errors

    def build(self, recipe_path: str, env: dict = None, **kwargs) -> str:
        """Start an asynchronous conda build process.

        Args:
            recipe_path: Path to recipe directory
            env: Dictionary of environment variables to set for build
            **kwargs: Additional build arguments including:
                config_file: Path to conda build config file
                croot: Build root directory
                channels: List of channels or single channel
                variant_config_files: List of variant config files
                python_version: Python version for build
                numpy_version: NumPy version for build
                output_folder: Output directory for built package

        Returns:
            str: Build ID that can be used to check status and logs

        Raises:
            ValueError: If any required paths don't exist
        """
        # Validate paths before starting build
        errors = self._validate_paths(
            recipe_path,
            kwargs.get('config_file'),
            kwargs.get('croot')
        )
        if errors:
            raise ValueError("\n".join(errors))

        args = ["build", recipe_path]
        args.extend(self.default_args)

        # Handle special cases for argument formatting
        if 'channels' in kwargs:
            channels = kwargs.pop('channels')
            if isinstance(channels, (list, tuple)):
                for channel in channels:
                    args.extend(["-c", str(channel)])
            else:
                args.extend(["-c", str(channels)])

        # Add remaining build arguments
        for key, value in kwargs.items():
            if isinstance(value, list):
                for v in value:
                    args.extend([f"--{key.replace('_', '-')}", str(v)])
            elif value is not None:
                args.extend([f"--{key.replace('_', '-')}", str(value)])

        # Generate unique build ID
        build_id = f"{int(time.time())}_{os.path.basename(recipe_path)}"
        log_file = self._get_log_file(build_id)

        # Start build process in background
        command = [self.binary_path] + self.sanitize_args(*args)
        thread = threading.Thread(
            target=self._run_build_process,
            args=(build_id, command, log_file)
        )
        thread.start()

        return build_id

    def get_build_status(self, build_id: str) -> dict:
        """Get the status of a build process.

        Args:
            build_id: The build ID returned from build()

        Returns:
            dict: Build status information
        """
        if build_id not in self.active_builds:
            return {'status': 'not_found'}

        build_info = self.active_builds[build_id]
        return {
            'status': build_info['status'],
            'start_time': build_info['start_time'].isoformat(),
            'end_time': build_info['end_time'].isoformat() if 'end_time' in build_info else None,
        }

    def get_build_log(self, build_id: str, tail: int = None) -> str:
        """Get the log output from a build process.

        Args:
            build_id: The build ID returned from build()
            tail: Number of lines to return from end of log (None for all)

        Returns:
            str: Build log output
        """
        if build_id not in self.active_builds:
            return "Build ID not found"

        log_file = self.active_builds[build_id]['log_file']
        if not log_file.exists():
            return "Log file not found"

        with open(log_file) as f:
            if tail:
                lines = f.readlines()[-tail:]
                return ''.join(lines)
            return f.read()