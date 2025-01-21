# condamcp/async_cmd.py

""" An asynchronous command runner that supports:
- Output logging to files with timestamps
- Status callbacks for process monitoring
- Shell and non-shell command execution
- Split or combined stdout/stderr output streams
- Command and argument sanitization/escaping for security
- Cross-platform compatibility (Windows/Unix)
- Working directory and environment variable customization
- Asynchronous stream reading with proper encoding handling
- Process status tracking including PID, return codes, and errors

The module provides the AsyncProcessRunner class for executing external commands safely
and asynchronously, with comprehensive logging and monitoring capabilities. """
import asyncio
import aiofiles
import logging
import os
import shlex
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Union, Dict, List, Sequence, Tuple
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ProcessStatus:
    cmd: str
    args: List[str]
    pid: int
    stdout: str
    stderr: str
    return_code: Optional[int] = None
    error: Optional[Exception] = None
    log_file: Optional[Path] = None
    stdout_log_file: Optional[Path] = None
    stderr_log_file: Optional[Path] = None
    process: Optional[asyncio.subprocess.Process] = None

class CommandError(Exception):
    """Raised when there's an issue with command validation"""
    pass

class AsyncProcessRunner:
    PATH_TRAVERSAL = re.compile(r'\.{2}')  # Only check for path traversal attempts
    
    def __init__(
        self,
        log_dir: Optional[Union[str, Path]] = None,
        shell: bool = False,
        shell_path: Optional[str] = None,
        split_output_streams: bool = False
    ):
        """
        Initialize the AsyncProcessRunner.
        
        Args:
            log_dir: Directory where log files will be stored. Required for logging to be possible.
            status_callback: Optional callback function that receives ProcessStatus updates
            shell: Whether to run commands through the shell
            shell_path: Path to shell executable to use when shell=True. If None, will use system default shell.
            split_output_streams: Whether to split stdout and stderr into separate files (default False)
        """
        self.log_dir = Path(log_dir) if log_dir else None
        self.shell = shell
        self.shell_path = shell_path
        self.split_output_streams = split_output_streams
        self.is_windows = sys.platform == "win32"
        
        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created log directory at {self.log_dir}")
        else:
            logger.info("Initialized without log directory - logging will not be available")

    def sanitize_command(self, command: str) -> str:
        """
        Basic command validation and shell escaping if needed.
        Prevents path traversal attempts while letting shlex handle proper escaping.
        """
        if self.PATH_TRAVERSAL.search(command):
            raise CommandError("Path traversal attempts are not allowed in commands")
            
        # Don't quote the entire command when shell=True since that breaks pipes
        # The shell itself will handle command parsing
        return command

    def sanitize_args(self, args: Sequence[Union[str, int, float]]) -> List[str]:
        """
        Basic argument validation and shell escaping if needed.
        Converts all arguments to strings and handles escaping.
        """
        str_args = [str(arg) for arg in args]
        
        for arg in str_args:
            if self.PATH_TRAVERSAL.search(arg):
                raise CommandError("Path traversal attempts are not allowed in arguments")
        
        if self.shell:
            return [shlex.quote(arg) for arg in str_args]
        return str_args

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for Windows compatibility.
        Removes characters that are invalid in Windows filenames.
        """
        # Remove Windows-invalid filename chars: < > : " / \ | ? *
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', filename)
        # Handle Windows reserved names (CON, PRN, AUX, etc.)
        reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3',
                         'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        name = sanitized.split('.')[0].upper()
        if name in reserved_names:
            sanitized = f"_{sanitized}"
        return sanitized

    def _get_log_files(self, cmd_name: str) -> Union[Path, Tuple[Path, Path]]:
        """
        Generate log file path(s).
        
        Args:
            cmd_name: Base name for the log file(s)
            
        Returns:
            Either a single Path for combined output or a tuple of (stdout_path, stderr_path)
        """
        if not self.log_dir:
            return None if not self.split_output_streams else (None, None)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize the command name for Windows compatibility
        safe_cmd_name = self._sanitize_filename(cmd_name)
        base_name = f"{safe_cmd_name}_{timestamp}"
        
        if self.split_output_streams:
            stdout_file = self.log_dir / f"{base_name}_stdout.log"
            stderr_file = self.log_dir / f"{base_name}_stderr.log"
            logger.debug(f"Created split log files: stdout={stdout_file}, stderr={stderr_file}")
            return stdout_file, stderr_file
        else:
            combined_file = self.log_dir / f"{base_name}_output.log"
            logger.debug(f"Created combined log file: {combined_file}")
            return combined_file

    async def _read_stream(
        self,
        stream: asyncio.StreamReader,
        log_file: Optional[Path],
        stream_name: str,
        status: Optional[ProcessStatus] = None,
        status_callback: Optional[Callable[[ProcessStatus], None]] = None
    ) -> str:
        """
        Read from a stream and optionally write to a log file.
        
        Args:
            stream: The stream to read from
            log_file: Optional file to write to
            stream_name: Name of the stream ('stdout' or 'stderr') for prefixing in combined output
            status: Current process status for incremental updates
            status_callback: Callback for incremental status updates
            
        Returns:
            Empty string since we don't accumulate output
        """
        if log_file:
            logger.debug(f"Starting to read {stream_name} and write to {log_file}")
            async with aiofiles.open(log_file, 'ab') as f:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    
                    decoded_line = line.decode(errors='replace').rstrip()
                    
                    # If we're using a combined log file, prefix the lines
                    if not self.split_output_streams:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_line = f"[{timestamp}] [{stream_name}] {decoded_line}\n".encode()
                    else:
                        log_line = line
                    
                    await f.write(log_line)
                    await f.flush()  # Ensure immediate writing
                    
                    # Send incremental status update if callback is provided
                    if status and status_callback:
                        # Create a new status object for each line
                        line_status = ProcessStatus(
                            cmd=status.cmd,
                            args=status.args,
                            pid=status.pid,
                            stdout=decoded_line if stream_name == 'stdout' else '',
                            stderr=decoded_line if stream_name == 'stderr' else '',
                            log_file=log_file if not self.split_output_streams else None,
                            stdout_log_file=log_file if self.split_output_streams and stream_name == 'stdout' else None,
                            stderr_log_file=log_file if self.split_output_streams and stream_name == 'stderr' else None
                        )
                        status_callback(line_status)
        else:
            logger.debug(f"Starting to read {stream_name} without file logging")
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded_line = line.decode(errors='replace').rstrip()
                
                # Send incremental status update if callback is provided
                if status and status_callback:
                    # Create a new status object for each line
                    line_status = ProcessStatus(
                        cmd=status.cmd,
                        args=status.args,
                        pid=status.pid,
                        stdout=decoded_line if stream_name == 'stdout' else '',
                        stderr=decoded_line if stream_name == 'stderr' else '',
                        log_file=None,
                        stdout_log_file=None,
                        stderr_log_file=None
                    )
                    status_callback(line_status)
        
        return ''

    async def execute(
        self,
        command: str,
        args: Optional[Sequence[Union[str, int, float]]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Union[str, Path]] = None,
        enable_logging: bool = True,
        timeout: Optional[float] = None,
        shell: Optional[bool] = None,
        status_callback: Optional[Callable[[ProcessStatus], None]] = None,
    ) -> ProcessStatus:
        """Run a command asynchronously with arguments.
        
        Args:
            command: The command to run
            args: Optional sequence of arguments
            env: Optional environment variables
            cwd: Optional working directory
            enable_logging: Whether to log output for this command (default True). 
                          Only works if log_dir was set during initialization.
            timeout: Optional timeout in seconds. If None, no timeout is applied.
                    If specified, raises asyncio.TimeoutError if command exceeds timeout.
            shell: Optional override for the shell setting. If None, uses the runner's shell setting.
        """
        process = None
        try:
            async def _run_with_timeout():
                nonlocal process
                stdout_file = stderr_file = None  # Initialize at start
                try:
                    use_shell = self.shell if shell is None else shell
                    sanitized_cmd = self.sanitize_command(command)
                    sanitized_args = self.sanitize_args(args or [])
                    
                    cmd_str = f"{sanitized_cmd} {' '.join(sanitized_args)}".strip()
                    # Get just the filename part of the command, handling Windows paths correctly
                    cmd_name = Path(sanitized_cmd).name
                    
                    logger.info(f"Starting command: {cmd_str}")
                    if env:
                        logger.debug(f"Environment variables: {env}")
                    if cwd:
                        cwd_path = Path(cwd)  # Ensure proper path handling
                        logger.debug(f"Working directory: {cwd_path}")

                    log_files = self._get_log_files(cmd_name) if (self.log_dir and enable_logging) else None
                    
                    if self.split_output_streams:
                        if log_files:
                            stdout_file, stderr_file = log_files
                    else:
                        stdout_file = stderr_file = log_files

                    if use_shell:
                        from .utils import get_default_shell
                        shell_executable = self.shell_path or get_default_shell()
                        
                        if isinstance(args, (list, tuple)) and args:
                            # Handle simple commands with arguments
                            shell_cmd = f"{sanitized_cmd} {' '.join(sanitized_args)}"
                        else:
                            # Handle complex shell commands (like those with pipes)
                            shell_cmd = sanitized_cmd
                        
                        process = await asyncio.create_subprocess_shell(
                            shell_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            env=env,
                            cwd=cwd_path if cwd else None,
                            executable=shell_executable
                        )
                    else:
                        process = await asyncio.create_subprocess_exec(
                            sanitized_cmd,
                            *sanitized_args,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            env=env,
                            cwd=cwd_path if cwd else None
                        )
                    
                    logger.info(f"Process started with PID {process.pid}")
                    
                    # Initial empty status
                    status = ProcessStatus(
                        cmd=sanitized_cmd,
                        args=sanitized_args,
                        pid=process.pid,
                        stdout='',
                        stderr='',
                    )
                    
                    if status_callback:
                        status_callback(status)
                    
                    # Read streams but don't accumulate output
                    await asyncio.gather(
                        self._read_stream(process.stdout, stdout_file, 'stdout', status, status_callback),
                        self._read_stream(process.stderr, stderr_file, 'stderr', status, status_callback)
                    )
                    
                    return_code = await process.wait()
                    logger.info(f"Process {process.pid} completed with return code {return_code}")
                    
                    # Final status with empty output strings since we don't accumulate
                    status = ProcessStatus(
                        cmd=sanitized_cmd,
                        args=sanitized_args,
                        pid=process.pid,
                        stdout='',
                        stderr='',
                        return_code=return_code,
                        log_file=stdout_file if not self.split_output_streams else None,
                        stdout_log_file=stdout_file if self.split_output_streams else None,
                        stderr_log_file=stderr_file if self.split_output_streams else None
                    )
                    
                    if status_callback:
                        status_callback(status)
                    
                    return status
                except Exception as e:
                    logger.error(f"Error running command: {e}")
                    status = ProcessStatus(
                        cmd=command,
                        args=args or [],
                        pid=process.pid if process else -1,
                        stdout='',
                        stderr=str(e),
                        error=e,
                        log_file=stdout_file if not self.split_output_streams else None,
                        stdout_log_file=stdout_file if self.split_output_streams else None,
                        stderr_log_file=stderr_file if self.split_output_streams else None
                    )
                    if status_callback:
                        status_callback(status)
                    raise

            if timeout is not None:
                try:
                    return await asyncio.wait_for(_run_with_timeout(), timeout=timeout)
                except asyncio.TimeoutError:
                    if process:
                        logger.warning(f"Process {process.pid} timed out, terminating...")
                        try:
                            process.terminate()
                            # Give it a chance to terminate gracefully
                            try:
                                await asyncio.wait_for(process.wait(), timeout=0.5)
                            except asyncio.TimeoutError:
                                logger.warning(f"Process {process.pid} did not terminate gracefully, killing...")
                                process.kill()
                                await process.wait()
                        except ProcessLookupError:
                            pass  # Process already terminated
                    raise
            else:
                return await _run_with_timeout()
        except Exception as e:
            # Ensure process is cleaned up even if something else goes wrong
            if process and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass  # Process already terminated
            raise

    async def fork(
        self,
        command: str,
        args: Optional[Sequence[Union[str, int, float]]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Union[str, Path]] = None,
        enable_logging: bool = True
    ) -> ProcessStatus:
        """Execute a command asynchronously in the background.
        
        This is similar to execute() but returns immediately without waiting for
        the command to complete. The command continues running in the background.
        Output is logged to files but not captured in memory.
        
        Args:
            command: The command to run
            args: Optional sequence of arguments
            env: Optional environment variables
            cwd: Optional working directory
            enable_logging: Whether to log output (default True)
            
        Returns:
            ProcessStatus with returncode=None since command is still running
        """
        try:
            sanitized_cmd = self.sanitize_command(command)
            sanitized_args = self.sanitize_args(args or [])
            
            cmd_str = f"{sanitized_cmd} {' '.join(sanitized_args)}".strip()
            cmd_name = Path(sanitized_cmd).name
            
            logger.info(f"Starting background command: {cmd_str}")
            if env:
                logger.debug(f"Environment variables: {env}")
            if cwd:
                cwd_path = Path(cwd)
                logger.debug(f"Working directory: {cwd_path}")

            # Get log files if logging is enabled
            log_files = self._get_log_files(cmd_name) if (self.log_dir and enable_logging) else None
            
            if self.shell:
                from .utils import get_default_shell
                shell_executable = self.shell_path or get_default_shell()
                shell_cmd = f"{sanitized_cmd} {' '.join(sanitized_args)}"
                
                process = await asyncio.create_subprocess_shell(
                    shell_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    cwd=cwd_path if cwd else None,
                    executable=shell_executable
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    sanitized_cmd,
                    *sanitized_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    cwd=cwd_path if cwd else None
                )

            logger.info(f"Background process started with PID {process.pid}")
            
            # Create initial status
            status = ProcessStatus(
                cmd=sanitized_cmd,
                args=sanitized_args,
                pid=process.pid,
                stdout='',
                stderr='',
                return_code=None,  # None indicates still running
                log_file=log_files if not self.split_output_streams else None,
                stdout_log_file=log_files[0] if self.split_output_streams else None,
                stderr_log_file=log_files[1] if self.split_output_streams else None,
                process=process  # Keep reference to process
            )

            # Start background tasks to read output streams
            if enable_logging:
                asyncio.create_task(self._read_stream(
                    process.stdout,
                    status.stdout_log_file if self.split_output_streams else status.log_file,
                    'stdout',
                    status
                ))
                asyncio.create_task(self._read_stream(
                    process.stderr,
                    status.stderr_log_file if self.split_output_streams else status.log_file,
                    'stderr',
                    status
                ))
            
            return status
            
        except Exception as e:
            logger.error(f"Error starting background command: {e}")
            return ProcessStatus(
                cmd=command,
                args=args or [],
                pid=-1,
                stdout='',
                stderr=str(e),
                error=e,
                log_file=None,
                stdout_log_file=None,
                stderr_log_file=None
            )
