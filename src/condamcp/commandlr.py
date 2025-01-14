# condamcp/commandlr.py

"""
A wrapper tool for executing shell commands.
"""

import shlex
import subprocess
from .utils import get_default_shell

class Commandlr:
    def __init__(self, shell=None, use_shell=False, timeout=60):
        """Initialize a shell command wrapper.

        Args:
            shell (str, optional): Path to shell executable. Defaults to system default shell.
            use_shell (bool, optional): Whether to run commands through shell. Defaults to False.
            timeout (int, optional): Command timeout in seconds. Defaults to 60.
        """
        self.default_shell = shell or get_default_shell()
        self.use_shell = use_shell
        self.timeout = timeout

    def sanitize_string(self, s):
        """Escape/sanitize a single string for shell usage.

        Args:
            s (str): String to sanitize.

        Returns:
            str: Shell-escaped version of the input string.
        """
        return shlex.quote(s)

    def sanitize_args(self, *args):
        """Escape/sanitize multiple command arguments for shell usage.

        Args:
            *args: Variable length argument list of strings to sanitize.

        Returns:
            list: List of shell-escaped strings.
        """
        return [self.sanitize_string(arg) for arg in args]

    def build_command(self, *args):
        """Build a command string from arguments.

        Args:
            *args: Variable length argument list of command components.

        Returns:
            str: Space-joined string of sanitized command arguments.

        Example:
            >>> cmd = Commandlr(use_shell=True)
            >>> cmd.build_command("ls", "-la")
            'ls -la'
        """
        return " ".join(self.sanitize_args(*args))

    def _exec_subprocess(self, command, timeout=60, cwd=None):
        """Execute a subprocess command.
        
        Args:
            command (list): Command and arguments to execute.
            timeout (int, optional): Command timeout in seconds. Defaults to 60.
            cwd (str, optional): Working directory. Defaults to None.
        
        Returns:
            subprocess.CompletedProcess: Result of the command execution.

        Note:
            This is an internal method used by runcmd().
        """
        if self.use_shell:
            # If using shell, join command into string and use shell executable
            cmd_str = " ".join(command)
            command = [self.default_shell, "-c", cmd_str]
        
        return subprocess.run(
            command,
            shell=False,  # We handle shell execution explicitly above
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True
        )

    def _handle_command_error(self, returncode, stdout, stderr, command_name="Command"):
        """Handle errors from command execution.
        
        Args:
            returncode (int): The return code from the command
            stdout (str): Standard output from the command
            stderr (str): Standard error from the command
            command_name (str, optional): Name of the command for error message. Defaults to "Command".
            
        Raises:
            RuntimeError: If the command failed (non-zero return code)
            
        Returns:
            tuple: The original (returncode, stdout, stderr) if no error
        """
        if returncode != 0:
            error_msg = f"{command_name} failed with return code {returncode}"
            if stderr:
                error_msg += f"\nError: {stderr}"
            if stdout:
                error_msg += f"\nOutput: {stdout}"
            raise RuntimeError(error_msg)
        return returncode, stdout, stderr

    def runcmd(self, *args, timeout=None, cwd=None):
        """Execute a command with the given arguments.

        Args:
            *args: Variable length argument list of command arguments.
            timeout (int, optional): Command timeout in seconds. Defaults to self.timeout.
            cwd (str, optional): Working directory for command execution. Defaults to None.

        Returns:
            tuple: A tuple containing:
                - returncode (int): The exit code of the command (0 typically means success)
                - stdout (str): The standard output from the command
                - stderr (str): The standard error output from the command

        Examples:
            >>> cmd = Commandlr(use_shell=True)
            >>> returncode, stdout, stderr = cmd.runcmd("ls", "-la")
            >>> returncode, stdout, stderr = cmd.runcmd("echo", "hello")
        """
        command = self.sanitize_args(*args)
        result = self._exec_subprocess(command, timeout=timeout, cwd=cwd)
        return self._handle_command_error(
            result.returncode, 
            result.stdout, 
            result.stderr,
            command_name=" ".join(args)
        )

