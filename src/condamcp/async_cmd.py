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
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Union, Dict, List, Sequence, Tuple, Any
from dataclasses import dataclass
import psutil
import json

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ProcessStatus:
    """A dataclass representing the status and output of an asynchronous process.

    This class tracks the state and output of a running or completed process,
    including its command, arguments, process ID, output streams, return code,
    and any errors that occurred during execution.

    Attributes:
        cmd (str): The command that was executed.
        args (List[str]): List of arguments passed to the command.
        pid (int): Process ID of the running or completed process.
        stdout (str): Standard output captured from the process.
        stderr (str): Standard error captured from the process.
        return_code (Optional[int]): Return code of the process. None if still running.
        error (Optional[Exception]): Any exception that occurred during execution.
        log_file (Optional[Path]): Path to the log file if output logging is enabled.
        process (Optional[asyncio.subprocess.Process]): Reference to the underlying asyncio process.
    """
    cmd: str
    args: List[str]
    pid: int
    stdout: str
    stderr: str
    return_code: Optional[int] = None
    error: Optional[Exception] = None
    log_file: Optional[Path] = None
    process: Optional[asyncio.subprocess.Process] = None

class CommandError(Exception):
    """Raised when there's an issue with command validation"""
    pass

class AsyncProcessRunner:
    PATH_TRAVERSAL = re.compile(r'\.{2}')  # Only check for path traversal attempts
    
    def __init__(
        self,
        log_dir: Optional[Union[str, Path]] = None,
        track_processes: bool = False,
        shell: bool = False,
        shell_path: Optional[str] = None
    ):
        """
        Initialize the AsyncProcessRunner.
        
        Args:
            log_dir: Directory where log files will be stored. If None, a temporary directory will be created.
            track_processes: Whether to enable ProcessStatus tracking for commands.
            shell: Whether to run commands through the shell
            shell_path: Path to shell executable to use when shell=True. If None, will use system default shell.
        """
        self.shell = shell
        self.shell_path = shell_path
        self.is_windows = sys.platform == "win32"
        self.track_processes = track_processes
        self._active_procs: Dict[int, ProcessStatus] = {}
        self._background_tasks: List[asyncio.Task] = []
        self._using_temp_dir = False
        
        if log_dir:
            self.log_dir = Path(log_dir).resolve()
            self.log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using specified log directory at {self.log_dir}")
        else:
            # Create a temporary directory for logs
            # The TemporaryDirectory context manager will handle cleanup automatically
            self._temp_dir_manager = tempfile.TemporaryDirectory(prefix="async_cmd_logs")
            self.log_dir = Path(self._temp_dir_manager.name).resolve()
            self._using_temp_dir = True
            logger.info(f"Created temporary log directory at {self.log_dir}")

    def get_active_processes(self) -> Dict[int, ProcessStatus]:
        """
        Get a dictionary of all currently active processes.
        """
        if not self.track_processes:
            raise RuntimeError("Process tracking is not enabled")
        return self._active_procs

    def get_process(self, pid: int) -> Dict[str, Any]:
        """Get detailed status of a command.
        
        Args:
            pid: Process ID of the command
            
        Returns:
            dict: Status information including:
                - status: 'not_found', 'running', 'completed', or 'failed'
                - return_code: Process return code (None if still running)
                - pid: Process ID
        """
        if not self.track_processes:
            raise RuntimeError("Process tracking is not enabled")
        
        if pid not in self._active_procs:
            return {'status': 'not_found', 'pid': pid, 'return_code': None}

        status = self._active_procs[pid]
        
        # Update return code from process if available
        if status.process:
            status.return_code = status.process.returncode

        # Determine status based on return code
        if status.return_code is None:
            state = 'running'
        elif status.return_code == 0:
            state = 'completed'
        else:
            state = 'failed'

        return {
            'status': state,
            'return_code': status.return_code,
            'pid': status.pid
        }
    
    def kill_process(self, pid: int):
        """Kill a specific process by its PID.
        
        Args:
            pid: Process ID of the process to kill
        """
        if not self.track_processes:
            raise RuntimeError("Process tracking is not enabled")
        if pid not in self._active_procs:
            raise ValueError(f"Process with PID {pid} not found in active processes")
        try:
            proc = psutil.Process(pid)
            
            # Try graceful termination first
            proc.terminate()
            
            try:
                # Give it a moment to terminate gracefully
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                # If still running after timeout, force kill
                logger.warning(f"Process {pid} did not terminate gracefully, forcing kill...")
                proc.kill()
                
        except psutil.NoSuchProcess:
            logger.debug(f"Process {pid} already terminated")
        except Exception as e:
            logger.error(f"Failed to kill process {pid}: {e}")
        
    def kill_all_processes(self):
        """Kill all tracked processes, attempting graceful termination first.
        
        On Unix systems, this sends SIGTERM first, then SIGKILL if needed.
        On Windows, this calls terminate() first, then kill() if needed.
        """
        if not self.track_processes:
            raise RuntimeError("Process tracking is not enabled")
        for pid, status in self._active_procs.items():
            if status.process and status.process.returncode is None:
                self.kill_process(pid)

    async def wait_for_command(self,pid, timeout_seconds=60):
        """ Asyncronous function to use to wait for a given process to finish 
        
        Args:
            pid: Process ID to wait for
            timeout_seconds: Maximum time to wait in seconds (default: 60)
        """
        iterations = int(timeout_seconds * 10)
        for _ in range(iterations):
            proc_status = self.get_process(pid)
            if proc_status['status'] in ['completed', 'failed']:
                break
            await asyncio.sleep(0.1)
        else:
            raise TimeoutError(f"Process {pid} did not complete within {timeout_seconds} seconds")

    def get_process_log(self, pid: int, tail: Optional[int] = None) -> str:
        """Get the log output from a process.
        
        Args:
            pid: Process ID of the command
            tail: Optional number of lines to return from end of log
            
        Returns:
            str: Log content or error message if logs not found
        """
        if pid not in self._active_procs:
            return "Process ID not found"

        status = self._active_procs[pid]
        
        # Check if log file exists
        if not status.log_file or not os.path.exists(status.log_file):
            raise FileNotFoundError(f"Log file not found: {status.log_file}")
            
        try:
            with open(status.log_file) as f:
                log_content = f.read()
                
            if not log_content:
                return log_content
                
            if tail:
                lines = log_content.splitlines()[-tail:]
                return '\n'.join(lines)
                
            return log_content
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            return f"Error reading log file: {str(e)}"

    def get_json_response(self, pid: int) -> Dict[str, Any]:
        """Load and parse the command output as JSON.
        
        This is a helper method for commands that output JSON data. It retrieves the raw
        command output from the log file and attempts to parse it as JSON.
        
        Args:
            pid: Process ID of the command that generated JSON output
            
        Returns:
            dict: The parsed JSON data
            
        Raises:
            ValueError: If the log file is empty or content cannot be parsed as JSON
            FileNotFoundError: If the log file for the process is not found
            RuntimeError: If process tracking is not enabled
        """
        if not self.track_processes:
            raise RuntimeError("Process tracking is not enabled")
            
        log_content = self.get_process_log(pid)
        if not log_content:
            raise ValueError("Log file is empty")
            
        try:
            return json.loads(log_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse command output as JSON: {e}")
            logger.error(f"Raw log content: {log_content}")
            raise ValueError(f"Failed to parse command output as JSON: {e}")

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

    def _get_log_files(self, cmd_name: str) -> Path:
        """
        Generate log file path.
        
        Args:
            cmd_name: Base name for the log file
            
        Returns:
            Path to the combined output log file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_cmd_name = self._sanitize_filename(cmd_name)
        combined_file = self.log_dir / f"{safe_cmd_name}_{timestamp}_output.log"
        logger.debug(f"Created log file: {combined_file}")
        return combined_file

    async def _fork_stream(
        self,
        stream: asyncio.StreamReader,
        log_file: Optional[Path],
        stream_name: str
    ) -> str:
        """Read from a stream and write it directly to the log file without modification.
        
        Args:
            stream: The stream to read from
            log_file: Optional file to write to
            stream_name: Name of the stream ('stdout' or 'stderr')
        """
        if log_file:
            logger.debug(f"Starting to read {stream_name} and write to {log_file}")
            async with aiofiles.open(log_file, 'ab') as f:
                while True:
                    chunk = await stream.read()
                    if not chunk:
                        break
                    await f.write(chunk)
        return ''

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
        """
        BUFFER_SIZE = 8192  # Read in 8KB chunks for better performance
        
        if log_file:
            logger.debug(f"Starting to read {stream_name} and write to {log_file}")
            # Use 'wb' mode for consistent line endings across platforms
            async with aiofiles.open(log_file, 'ab') as f:
                while True:
                    try:
                        # Read a chunk of data
                        chunk = await stream.read(BUFFER_SIZE)
                        if not chunk:
                            break
                            
                        # Process the chunk line by line
                        lines = chunk.decode(errors='replace').splitlines(True)  # Keep line endings
                        
                        # Write all lines to log file with consistent line endings
                        for line in lines:
                            await f.write(line.rstrip().encode() + b"\r\n" if self.is_windows else b"\n")
                        
                        # Only flush periodically to improve performance
                        if len(chunk) < BUFFER_SIZE:  # Smaller chunk means less data coming
                            await f.flush()
                            
                        # Send status update if callback is provided (only for non-empty lines)
                        if status and status_callback:
                            for line in lines:
                                if line.strip():  # Only send non-empty lines to callback
                                    line_status = ProcessStatus(
                                        cmd=status.cmd,
                                        args=status.args,
                                        pid=status.pid,
                                        stdout=line.rstrip() if stream_name == 'stdout' else '',
                                        stderr=line.rstrip() if stream_name == 'stderr' else '',
                                        log_file=log_file,
                                        process=status.process
                                    )
                                    status_callback(line_status)
                                    
                    except Exception as e:
                        logger.error(f"Error reading from {stream_name}: {e}")
                        break
                        
        else:
            logger.debug(f"Starting to read {stream_name} without file logging")
            while True:
                try:
                    chunk = await stream.read(BUFFER_SIZE)
                    if not chunk:
                        break
                        
                    # Process chunk line by line for callbacks
                    if status and status_callback:
                        lines = chunk.decode(errors='replace').splitlines()
                        for line in lines:
                            if line.strip():  # Skip empty lines
                                line_status = ProcessStatus(
                                    cmd=status.cmd,
                                    args=status.args,
                                    pid=status.pid,
                                    stdout=line if stream_name == 'stdout' else '',
                                    stderr=line if stream_name == 'stderr' else '',
                                    log_file=None,
                                    process=status.process
                                )
                                status_callback(line_status)
                                
                except Exception as e:
                    logger.error(f"Error reading from {stream_name}: {e}")
                    break
        
        return ''

    async def execute(
        self,
        command: str,
        args: Optional[Sequence[Union[str, int, float]]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Union[str, Path]] = None,
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
            timeout: Optional timeout in seconds. If None, no timeout is applied.
            shell: Override the default shell setting for this command
            status_callback: Optional callback for incremental status updates
            
        Returns:
            ProcessStatus containing command results and metadata
        """
        process = None
        try:
            async def _run_with_timeout():
                nonlocal process
                log_file = None  # Initialize at start
                try:
                    use_shell = self.shell if shell is None else shell
                    sanitized_cmd = self.sanitize_command(command)
                    sanitized_args = self.sanitize_args(args or [])
                    
                    cmd_str = f"{sanitized_cmd} {' '.join(sanitized_args)}".strip()
                    cmd_name = Path(sanitized_cmd).name
                    
                    logger.info(f"Starting command: {cmd_str}")
                    if env:
                        logger.debug(f"Environment variables: {env}")
                    if cwd:
                        cwd_path = Path(cwd)
                        logger.debug(f"Working directory: {cwd_path}")

                    log_file = self._get_log_files(cmd_name)

                    if use_shell:
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
                    
                    logger.info(f"Process started with PID {process.pid}")
                    
                    # Initial empty status
                    status = ProcessStatus(
                        cmd=sanitized_cmd,
                        args=sanitized_args,
                        pid=process.pid,
                        stdout='',
                        stderr='',
                        log_file=log_file,
                        process=process
                    )
                    
                    if status_callback:
                        status_callback(status)
                    
                    # Read streams but don't accumulate output
                    await asyncio.gather(
                        self._read_stream(process.stdout, log_file, 'stdout', status, status_callback),
                        self._read_stream(process.stderr, log_file, 'stderr', status, status_callback)
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
                        log_file=log_file,
                        process=process
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
                        log_file=log_file,
                        process=process
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

    async def _clean_background_tasks(self):
        """Clean up any background tasks."""
        if self._background_tasks:
            # Wait for all background tasks to complete
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()

    async def _kill_all_processes(self):
        """Kill all tracked processes, attempting graceful termination first.
        
        On Unix systems, this sends SIGTERM first, then SIGKILL if needed.
        On Windows, this calls terminate() first, then kill() if needed.
        """
        if not self.track_processes:
            raise RuntimeError("Process tracking is not enabled")

        for pid, status in list(self._active_procs.items()):
            if status.process and status.process.returncode is None:
                try:
                    logger.info(f"Terminating process {pid}")
                    status.process.terminate()
                    try:
                        # Give it a moment to terminate gracefully
                        await asyncio.wait_for(status.process.wait(), timeout=3)
                    except asyncio.TimeoutError:
                        # If still running after timeout, force kill
                        logger.warning(f"Process {pid} did not terminate gracefully, forcing kill...")
                        status.process.kill()
                        await status.process.wait()
                except ProcessLookupError:
                    logger.debug(f"Process {pid} already terminated")
                except Exception as e:
                    logger.error(f"Failed to kill process {pid}: {e}")

    async def teardown(self):
        """Clean up any tracked processes and background tasks."""
        await self._kill_all_processes()
        await self._clean_background_tasks()

    async def fork(
        self,
        command: str,
        args: Optional[Sequence[Union[str, int, float]]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Union[str, Path]] = None,
        shell: Optional[bool] = None
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
            shell: Override the default shell setting for this command
            
        Returns:
            ProcessStatus with returncode=None since command is still running
        """
        try:
            use_shell = self.shell if shell is None else shell
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
            log_file = self._get_log_files(cmd_name)
            
            if use_shell:
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
                log_file=log_file,
                process=process  # Keep reference to process
            )

            # Track the process if tracking is enabled
            if self.track_processes:
                self._active_procs[process.pid] = status

            # Start background tasks to read output streams and track them
            stdout_task = asyncio.create_task(self._fork_stream(
                process.stdout,
                status.log_file,
                'stdout'
            ))
            stderr_task = asyncio.create_task(self._fork_stream(
                process.stderr,
                status.log_file,
                'stderr'
            ))
            
            self._background_tasks.extend([stdout_task, stderr_task])
            
            return status
            
        except Exception as e:
            logger.error(f"Error starting background command: {e}")
            status = ProcessStatus(
                cmd=command,
                args=args or [],
                pid=-1,
                stdout='',
                stderr=str(e),
                error=e,
                log_file=None,
                process=None
            )
            if self.track_processes:
                self._active_procs[-1] = status
            return status
