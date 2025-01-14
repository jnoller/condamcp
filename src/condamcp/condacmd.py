# condacmd.py

"""
Conda command wrapper that uses `commandlr` to build and execute commands.
"""

from .commandlr import Commandlr
from .utils import get_default_conda_binary
import json

class Condacmd(Commandlr):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binary_path = get_default_conda_binary()

    def _parse_json_response(self, response):
        """Parse a JSON response from a conda command"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from conda command")
    
    def env(self, *args, **kwargs):
        """Run a conda environment command."""
        return self.runcmd(self.binary_path, "env", *args, **kwargs)
    
    def env_list(self, as_json=False, verbose=False, quiet=False):
        """List all conda environments."""
        args = ["env", "list"]

        if as_json:
            args.append("--json")
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")

        command = [self.binary_path] + args
        returncode, stdout, stderr = self.runcmd(*command)
        
        if as_json:
            return self._parse_json_response(stdout)
        return stdout

    def env_create(self, name=None, prefix=None, file=None, packages=None, dry_run=False, quiet=False, as_json=False, **kwargs):
        """Create a conda environment."""
        if file:
            args = ["env", "create"]
            if file:
                args.extend(["-f", file])
        else:
            # If no file specified, use conda create directly
            args = ["create"]
            if packages:
                args.extend(packages)

        # Handle environment specification
        if name and prefix:
            raise ValueError("Cannot specify both name and prefix")
        if name:
            args.extend(["-n", name])
        if prefix:
            args.extend(["-p", prefix])

        # Always add -y to avoid prompts
        args.append("-y")

        # Handle flags
        if dry_run:
            args.append("-d")
        if quiet:
            args.append("-q")
        if as_json:
            args.append("--json")

        # Add any additional keyword arguments
        for key, value in kwargs.items():
            if len(key) == 1:
                args.append(f"-{key}")
            else:
                args.append(f"--{key.replace('_', '-')}")
            if value is not True:  # Don't add value for boolean flags
                args.append(str(value))

        # Execute the command with full command path for error message
        command = [self.binary_path] + args
        returncode, stdout, stderr = self.runcmd(*command)
        
        if as_json:
            return self._parse_json_response(stdout)
        return returncode, stdout, stderr

    def env_remove(self, name=None, prefix=None, dry_run=False, quiet=False, as_json=False, yes=True, verbose=False, solver=None, console=None):
        """Remove a conda environment.

        You must deactivate the existing environment before you can remove it.

        Args:
            name (str, optional): Name of environment. Defaults to None.
            prefix (str, optional): Full path to environment location. Defaults to None.
            dry_run (bool, optional): Only display what would have been done. Defaults to False.
            quiet (bool, optional): Do not display progress bar. Defaults to False.
            as_json (bool, optional): Return output as parsed JSON. Defaults to False.
            yes (bool, optional): Don't ask for confirmation. Defaults to True.
            verbose (bool, optional): Increase output verbosity. Defaults to False.
            solver (str, optional): Choose solver backend ('classic' or 'libmamba'). Defaults to None.
            console (str, optional): Select the backend for output rendering. Defaults to None.

        Returns:
            If as_json=False:
                tuple: (returncode, stdout, stderr) from the command execution.
            If as_json=True:
                dict: Parsed JSON output from conda.

        Raises:
            ValueError: If both name and prefix are specified, or if neither is specified.

        Examples:
            >>> conda = Condacmd()
            >>> # Remove by name
            >>> conda.env_remove(name="myenv")
            >>> # Remove by prefix with JSON output
            >>> result = conda.env_remove(prefix="/path/to/env", as_json=True)
            >>> # Dry run with specific solver
            >>> conda.env_remove(name="myenv", dry_run=True, solver="libmamba")
        """
        args = ["env", "remove"]

        # Handle environment specification
        if name and prefix:
            raise ValueError("Cannot specify both name and prefix")
        if not (name or prefix):
            raise ValueError("Must specify either name or prefix")
        
        if name:
            args.extend(["-n", name])
        if prefix:
            args.extend(["-p", prefix])

        # Handle flags
        if dry_run:
            args.append("-d")
        if quiet:
            args.append("-q")
        if as_json:
            args.append("--json")
        if yes:
            args.append("-y")
        if verbose:
            args.append("-v")
        if solver:
            args.extend(["--solver", solver])
        if console:
            args.extend(["--console", console])

        # Execute the command
        returncode, stdout, stderr = self.runcmd(self.binary_path, *args)
        
        if as_json:
            return self._parse_json_response(stdout)
        return returncode, stdout, stderr

    def env_export(self, name=None, prefix=None, file=None, channels=None, 
                  no_builds=False, ignore_channels=False, from_history=False,
                  override_channels=False, as_json=False, verbose=False, 
                  quiet=False, console=None):
        """Export a conda environment specification.

        Args:
            name (str, optional): Name of environment. Defaults to None.
            prefix (str, optional): Full path to environment location. Defaults to None.
            file (str, optional): Output file path. Defaults to None (stdout).
            channels (list, optional): Additional channels to include. Defaults to None.
            no_builds (bool, optional): Remove build specification from dependencies. Defaults to False.
            ignore_channels (bool, optional): Do not include channel names with package names. Defaults to False.
            from_history (bool, optional): Build environment spec from explicit specs in history. Defaults to False.
            override_channels (bool, optional): Do not include .condarc channels. Defaults to False.
            as_json (bool, optional): Return output as parsed JSON. Defaults to False.
            verbose (bool, optional): Increase output verbosity. Defaults to False.
            quiet (bool, optional): Do not display progress bar. Defaults to False.
            console (str, optional): Select the backend for output rendering. Defaults to None.

        Returns:
            If as_json=False and file=None:
                str: The environment specification as YAML
            If as_json=True:
                dict: The environment specification as a dictionary
            If file is specified:
                tuple: (returncode, stdout, stderr) from the command execution

        Raises:
            ValueError: If both name and prefix are specified.

        Examples:
            >>> conda = Condacmd()
            >>> # Export current environment to stdout
            >>> print(conda.env_export())
            >>> # Export specific environment to file
            >>> conda.env_export(name="myenv", file="environment.yml")
            >>> # Export with additional options
            >>> spec = conda.env_export(
            ...     name="myenv",
            ...     no_builds=True,
            ...     from_history=True,
            ...     channels=["conda-forge"]
            ... )
        """
        args = ["env", "export"]

        # Handle environment specification
        if name and prefix:
            raise ValueError("Cannot specify both name and prefix")
        if name:
            args.extend(["-n", name])
        if prefix:
            args.extend(["-p", prefix])

        # Handle file output
        if file:
            args.extend(["-f", file])

        # Handle channels
        if channels:
            for channel in channels:
                args.extend(["-c", channel])
        
        # Handle flags
        if override_channels:
            args.append("--override-channels")
        if no_builds:
            args.append("--no-builds")
        if ignore_channels:
            args.append("--ignore-channels")
        if from_history:
            args.append("--from-history")
        if as_json:
            args.append("--json")
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")
        if console:
            args.extend(["--console", console])

        # Execute command
        command = [self.binary_path] + args
        returncode, stdout, stderr = self.runcmd(*command)

        # Handle output based on flags and file
        if file:
            return returncode, stdout, stderr
        if as_json:
            return self._parse_json_response(stdout)
        return stdout

    def show_help(self, command: str = None):
        """Get help information for conda commands.

        Args:
            command: The conda command to show help for (e.g., "build", "env create")
                    If not provided, shows general conda help.

        Returns:
            tuple: (returncode, stdout, stderr)
        """
        if command is None:
            return self.runcmd(self.binary_path, "help")
        else:
            # Split command string into parts and add --help
            cmd_parts = command.split()
            return self.runcmd(self.binary_path, *cmd_parts, "--help")