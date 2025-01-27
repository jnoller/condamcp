# condacmd.py

"""
Conda command wrapper that uses `commandlr` to build and execute commands.
"""

from .async_cmd import AsyncProcessRunner, ProcessStatus
from .utils import get_default_conda_binary
import json
from typing import List, Optional, Callable, Dict, Union, Tuple, Literal
from enum import Enum

class CondaEnvCommand(str, Enum):
    """Valid subcommands for conda env"""
    CONFIG = "config"
    CREATE = "create"
    EXPORT = "export"
    LIST = "list"
    REMOVE = "remove"
    UPDATE = "update"

class AsyncCondaCmd(AsyncProcessRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binary_path = get_default_conda_binary()
    
    async def _parse_json_output(self, status: ProcessStatus, output_lines: List[str]) -> tuple[ProcessStatus, dict]:
        """Parse accumulated output lines as JSON.
        
        Args:
            status: The final ProcessStatus from the command
            output_lines: List of output lines to parse as JSON
            
        Returns:
            tuple: (ProcessStatus, dict) containing the status and parsed JSON
            
        Raises:
            ValueError: If JSON parsing fails
        """
        try:
            json_result = json.loads(''.join(output_lines))
            return status, json_result
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response from conda command")
    
    async def env(
        self,
        command: Union[CondaEnvCommand, Literal["config", "create", "export", "list", "remove", "update"]],
        name: Optional[str] = None,
        prefix: Optional[str] = None,
        packages: Optional[List[str]] = None,
        channels: Optional[List[str]] = None,
        override_channels: bool = False,
        use_local: bool = False,
        as_json: bool = False,
        quiet: bool = False,
        verbose: bool = False,
        offline: bool = False,
    ) -> ProcessStatus:
        """Execute a conda environment command asynchronously.

        This tool provides access to various conda environment commands. The command output
        is tracked and logged without modification, preserving any structured data formats.
        
        Args:
            command: The environment subcommand to run:
                - config: Configure a conda environment
                - create: Create an environment based on an environment definition file
                - export: Export a given environment
                - list: List all conda environments (alias for `conda info --envs`)
                - remove: Remove an environment
                - update: Update the current environment based on environment file
            name: Name of environment
            prefix: Full path to environment location (i.e. prefix)
            packages: List of packages to install in the environment
            channels: Additional channels to search for packages
            override_channels: Do not search default or .condarc channels
            use_local: Use locally built packages
            as_json: Add --json flag to get JSON formatted output
            quiet: Do not display progress bar
            verbose: Show additional output details
            offline: Work offline (don't connect to the Internet)
            
        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        cmd_args = ["env", command]
        
        # Handle environment specification
        if name:
            cmd_args.extend(["-n", name])
        if prefix:
            cmd_args.extend(["-p", prefix])
            
        # Handle package specs
        if packages:
            cmd_args.extend(packages)
            
        # Handle channels
        if channels:
            for channel in channels:
                cmd_args.extend(["-c", channel])
        if use_local:
            cmd_args.append("--use-local")
        if override_channels:
            cmd_args.append("--override-channels")
            
        # Handle output options
        if as_json:
            cmd_args.append("--json")
        if verbose:
            cmd_args.append("-v")
        if quiet:
            cmd_args.append("-q")
            
        # Handle networking options
        if offline:
            cmd_args.append("--offline")
            
        # Handle special cases for specific commands
        if command == "create":
            cmd_args.append("-y")  # Always add -y to avoid prompts for create
            
        # Fork the process and enable logging
        return await self.fork(
            self.binary_path,
            cmd_args
        )

    async def remove(
        self,
        name: Optional[str] = None,
        prefix: Optional[str] = None,
        packages: Optional[List[str]] = None,
        all: bool = False,
        keep_env: bool = False,
        channels: Optional[List[str]] = None,
        use_local: bool = False,
        override_channels: bool = False,
        repodata_fn: Optional[List[str]] = None,
        experimental: Optional[str] = None,
        no_lock: bool = False,
        repodata_use_zst: Optional[bool] = None,
        features: bool = False,
        force_remove: bool = False,
        no_pin: bool = False,
        solver: Optional[str] = None,
        use_index_cache: bool = False,
        insecure: bool = False,
        offline: bool = False,
        dry_run: bool = False,
        yes: bool = True,
        quiet: bool = False,
        as_json: bool = False,
        verbose: bool = False,
        console: Optional[str] = None,
        dev: bool = False,
        status_callback: Optional[Callable] = None
    ) -> ProcessStatus:
        """Remove packages from a conda environment asynchronously.
        
        Args:
            name: Name of environment
            prefix: Full path to environment location (i.e. prefix)
            packages: List of packages to remove
            all: Remove all packages
            keep_env: Keep the environment
            channels: Additional channels to search for packages
            use_local: Use locally built packages
            override_channels: Do not search default or .condarc channels
            repodata_fn: Specify file names of repodata on remote server
            experimental: Enable experimental features ('jlap' or 'lock')
            no_lock: Disable locking when reading/updating index cache
        
        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["remove"]
        
        # Handle environment specification
        if name:
            args.extend(["-n", name])
        if prefix:
            args.extend(["-p", prefix])
            
        # Handle package specs
        if packages:
            args.extend(packages)
            
        # Add options
        if all:
            args.append("--all")
        if keep_env:
            args.append("--keep-env")
        if channels:
            for channel in channels:
                args.extend(["-c", channel])
        if use_local:
            args.append("--use-local")
        if override_channels:
            args.append("--override-channels")
        if repodata_fn:
            for fn in repodata_fn:
                args.extend(["--repodata-fn", fn])
        if experimental:
            args.extend(["--experimental", experimental])
        if no_lock:
            args.append("--no-lock")
        if repodata_use_zst is not None:
            args.append("--repodata-use-zst" if repodata_use_zst else "--no-repodata-use-zst")
        if features:
            args.append("--features")
        if force_remove:
            args.append("--force-remove")
        if no_pin:
            args.append("--no-pin")
        if solver:
            args.extend(["--solver", solver])
        if use_index_cache:
            args.append("-C")
        if insecure:
            args.append("-k")
        if offline:
            args.append("--offline")
        if dry_run:
            args.append("-d")
        if yes:
            args.append("-y")
        if as_json:
            args.append("--json")
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")
        if console:
            args.extend(["--console", console])
        if dev:
            args.append("--dev")

        return await self.fork(self.binary_path, args)

    async def create(
        self,
        name: Optional[str] = None,
        prefix: Optional[str] = None,
        packages: Optional[List[str]] = None,
        clone: Optional[str] = None,
        file: Optional[str] = None,
        channels: Optional[List[str]] = None,
        use_local: bool = False,
        override_channels: bool = False,
        repodata_fn: Optional[List[str]] = None,
        experimental: Optional[str] = None,
        no_lock: bool = False,
        repodata_use_zst: Optional[bool] = None,
        strict_channel_priority: bool = False,
        no_channel_priority: bool = False,
        no_deps: bool = False,
        only_deps: bool = False,
        no_pin: bool = False,
        no_default_packages: bool = False,
        copy: bool = False,
        no_shortcuts: bool = False,
        shortcuts_only: Optional[List[str]] = None,
        use_index_cache: bool = False,
        insecure: bool = False,
        offline: bool = False,
        solver: Optional[str] = None,
        dry_run: bool = False,
        yes: bool = True,
        quiet: bool = False,
        as_json: bool = False,
        verbose: bool = False,
        console: Optional[str] = None,
        download_only: bool = False,
        show_channel_urls: bool = False,
        subdir: Optional[str] = None,
        dev: bool = False,
    ):
        """Create a new conda environment from a list of specified packages.

        To use the newly-created environment, use 'conda activate envname'.
        This command requires either the -n NAME or -p PREFIX option.

        Args:
            name (str, optional): Name of environment
            prefix (str, optional): Full path to environment location (i.e. prefix)
            packages (list[str], optional): List of packages to install in the environment
            clone (str, optional): Create a new environment as a copy of an existing local environment
            file (str, optional): Read package versions from the given file
            channels (list[str], optional): Additional channels to search for packages
            use_local (bool): Use locally built packages (identical to '-c local')
            override_channels (bool): Do not search default or .condarc channels
            repodata_fn (list[str], optional): Specify file names of repodata on remote server
            experimental (str, optional): Enable experimental features ('jlap' or 'lock')
            no_lock (bool): Disable locking when reading/updating index cache
            repodata_use_zst (bool, optional): Check for repodata.json.zst
            strict_channel_priority (bool): Packages in lower priority channels are not considered
            no_channel_priority (bool): Package version takes precedence over channel priority
            no_deps (bool): Do not install dependencies
            only_deps (bool): Only install dependencies
            no_pin (bool): Ignore pinned file
            no_default_packages (bool): Ignore create_default_packages in .condarc
            copy (bool): Install all packages using copies instead of hard- or soft-linking
            no_shortcuts (bool): Don't install start menu shortcuts
            shortcuts_only (list[str], optional): Install shortcuts only for specified packages
            use_index_cache (bool): Use cache of channel index files even if expired
            insecure (bool): Allow "insecure" SSL connections and transfers
            offline (bool): Offline mode, don't connect to the Internet
            solver (str, optional): Choose solver backend ('classic' or 'libmamba')
            dry_run (bool): Only display what would have been done
            yes (bool): Do not ask for confirmation
            quiet (bool): Do not display progress bar
            as_json (bool): Report all output as json
            verbose (bool): Show additional output details
            console (str, optional): Select the backend for output rendering
            download_only (bool): Solve environment and populate caches but don't install
            show_channel_urls (bool): Show channel urls
            subdir (str, optional): Use packages built for this platform
            dev (bool): Use sys.executable -m conda in wrapper scripts

        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["create"]
        
        # Handle environment specification
        if name:
            args.extend(["-n", name])
        if prefix:
            args.extend(["-p", prefix])
            
        # Handle package specs and sources
        if packages:
            args.extend(packages)
        if clone:
            args.extend(["--clone", clone])
        if file:
            args.extend(["--file", file])
            
        # Handle channels
        if channels:
            for channel in channels:
                args.extend(["-c", channel])
        if use_local:
            args.append("--use-local")
        if override_channels:
            args.append("--override-channels")
        if repodata_fn:
            for fn in repodata_fn:
                args.extend(["--repodata-fn", fn])
        if experimental:
            args.extend(["--experimental", experimental])
        if no_lock:
            args.append("--no-lock")
        if repodata_use_zst is not None:
            args.append("--repodata-use-zst" if repodata_use_zst else "--no-repodata-use-zst")
            
        # Handle solver options
        if strict_channel_priority:
            args.append("--strict-channel-priority")
        if no_channel_priority:
            args.append("--no-channel-priority")
        if no_deps:
            args.append("--no-deps")
        if only_deps:
            args.append("--only-deps")
        if no_pin:
            args.append("--no-pin")
        if no_default_packages:
            args.append("--no-default-packages")
        if solver:
            args.extend(["--solver", solver])
            
        # Handle package linking options
        if copy:
            args.append("--copy")
        if no_shortcuts:
            args.append("--no-shortcuts")
        if shortcuts_only:
            for pkg in shortcuts_only:
                args.extend(["--shortcuts-only", pkg])
                
        # Handle networking options
        if use_index_cache:
            args.append("-C")
        if insecure:
            args.append("-k")
        if offline:
            args.append("--offline")
            
        # Handle output options
        if dry_run:
            args.append("-d")
        if yes:
            args.append("-y")
        if as_json:
            args.append("--json")
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")
        if console:
            args.extend(["--console", console])
        if download_only:
            args.append("--download-only")
        if show_channel_urls:
            args.append("--show-channel-urls")
            
        # Handle platform options
        if subdir:
            args.extend(["--subdir", subdir])
            
        # Handle development options
        if dev:
            args.append("--dev")
            
        # Fork the process and enable logging
        return await self.fork(self.binary_path, args)
    
    async def export(
        self,
        name: Optional[str] = None,
        prefix: Optional[str] = None,
        file: Optional[str] = None,
        channels: Optional[List[str]] = None,
        override_channels: bool = False,
        no_builds: bool = False,
        ignore_channels: bool = False,
        from_history: bool = False,
        as_json: bool = False,
        console: Optional[str] = None,
        verbose: bool = False,
        quiet: bool = False,
    ):
        """Export a given environment.
        
        This tool exports the specification of a conda environment, which can be used
        to recreate the environment on another system.
        
        Args:
            name: Name of environment
            prefix: Full path to environment location (i.e. prefix)
            file: File name or path for the exported environment
            channels: Additional channels to include in the export
            override_channels: Do not include .condarc channels
            no_builds: Remove build specification from dependencies
            ignore_channels: Do not include channel names with package names
            from_history: Build environment spec from explicit specs in history
            as_json: Report all output as json
            console: Select the backend for output rendering
            verbose: Show additional output details
            quiet: Do not display progress bar
            
        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["export"]

        # Handle environment specification
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
        if override_channels:
            args.append("--override-channels")

        # Handle export options
        if no_builds:
            args.append("--no-builds")
        if ignore_channels:
            args.append("--ignore-channels")
        if from_history:
            args.append("--from-history")

        # Handle output options
        if as_json:
            args.append("--json")
        if console:
            args.extend(["--console", console])
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")

        return await self.fork(self.binary_path, args)
    
    async def help(self, command: Optional[str] = None) -> ProcessStatus:
        """Get help information for conda commands.

        Args:
            command (str, optional): The conda command to show help for (e.g., "build", "env create")
                                   If not provided, shows general conda help.
            status_callback (callable): Optional callback for process status updates

        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = []
        if command:
            # Split the command into parts and add them to args
            args.extend(command.split())
        args.append("--help")

        return await self.fork(self.binary_path, args)

    async def clean(
        self,
        all: bool = False,
        index_cache: bool = False,
        packages: bool = False,
        tarballs: bool = False,
        force_pkgs_dirs: bool = False,
        tempfiles: Optional[List[str]] = None,
        logfiles: bool = False,
        dry_run: bool = False,
        yes: bool = True,
        quiet: bool = False,
        as_json: bool = False,
        verbose: bool = False,
        console: Optional[str] = None,
    ):
        """Remove unused packages and caches.

        This tool removes unused conda packages and caches to free up disk space.
        It can clean various types of conda caches and temporary files.

        Args:
            all: Remove index cache, lock files, unused cache packages, tarballs, and logfiles
            index_cache: Remove index cache
            packages: Remove unused packages from writable package caches
            tarballs: Remove cached package tarballs
            force_pkgs_dirs: Remove *all* writable package caches
            tempfiles: Remove temporary files from specified environments
            logfiles: Remove log files
            dry_run: Only display what would have been done
            yes: Do not ask for confirmation
            quiet: Do not display progress bar
            as_json: Report all output as json
            verbose: Show additional output details
            console: Select the backend for output rendering
            status_callback: Optional callback for process status updates

        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["clean"]
        
        # Handle removal targets
        if all:
            args.append("--all")
        if index_cache:
            args.append("--index-cache")
        if packages:
            args.append("--packages")
        if tarballs:
            args.append("--tarballs")
        if force_pkgs_dirs:
            args.append("--force-pkgs-dirs")
        if tempfiles:
            args.append("--tempfiles")
            args.extend(tempfiles)
        if logfiles:
            args.append("--logfiles")
            
        # Handle output options
        if dry_run:
            args.append("-d")
        if yes:
            args.append("-y")
        if as_json:
            args.append("--json")
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")
        if console:
            args.extend(["--console", console])

        return await self.fork(self.binary_path, args)

    async def upgrade(
        self,
        packages: Optional[List[str]] = None,
        name: Optional[str] = None,
        prefix: Optional[str] = None,
        channels: Optional[List[str]] = None,
        use_local: bool = False,
        override_channels: bool = False,
        repodata_fn: Optional[List[str]] = None,
        experimental: Optional[str] = None,
        no_lock: bool = False,
        repodata_use_zst: Optional[bool] = None,
        strict_channel_priority: bool = False,
        no_channel_priority: bool = False,
        no_deps: bool = False,
        only_deps: bool = False,
        no_pin: bool = False,
        solver: Optional[str] = None,
        force_reinstall: bool = False,
        freeze_installed: bool = False,
        update_deps: bool = False,
        satisfied_skip_solve: bool = False,
        update_all: bool = False,
        update_specs: bool = False,
        copy: bool = False,
        no_shortcuts: bool = False,
        shortcuts_only: Optional[List[str]] = None,
        clobber: bool = False,
        use_index_cache: bool = False,
        insecure: bool = False,
        offline: bool = False,
        dry_run: bool = False,
        yes: bool = True,
        quiet: bool = False,
        as_json: bool = False,
        verbose: bool = False,
        console: Optional[str] = None,
        download_only: bool = False,
        show_channel_urls: bool = False,
        file: Optional[str] = None,
    ):
        """Update conda packages to the latest compatible version.

        This tool updates packages in a conda environment to their latest compatible versions.
        It handles dependency resolution and ensures package compatibility is maintained.

        Args:
            packages: List of packages to update in the conda environment
            name: Name of environment
            prefix: Full path to environment location (i.e. prefix)
            channels: Additional channels to search for packages
            use_local: Use locally built packages (identical to '-c local')
            override_channels: Do not search default or .condarc channels
            repodata_fn: Specify file names of repodata on remote server
            experimental: Enable experimental features ('jlap' or 'lock')
            no_lock: Disable locking when reading/updating index cache
            repodata_use_zst: Check for repodata.json.zst
            strict_channel_priority: Packages in lower priority channels are not considered
            no_channel_priority: Package version takes precedence over channel priority
            no_deps: Do not install dependencies
            only_deps: Only install dependencies
            no_pin: Ignore pinned file
            solver: Choose solver backend ('classic' or 'libmamba')
            force_reinstall: Ensure that any user-requested package is reinstalled
            freeze_installed: Do not update or change already-installed dependencies
            update_deps: Update dependencies that have available updates
            satisfied_skip_solve: Exit early if the requested specs are satisfied
            update_all: Update all installed packages in the environment
            update_specs: Update based on provided specifications
            copy: Install all packages using copies instead of hard- or soft-linking
            no_shortcuts: Don't install start menu shortcuts
            shortcuts_only: Install shortcuts only for specified packages
            clobber: Allow clobbering of overlapping file paths within packages
            use_index_cache: Use cache of channel index files even if expired
            insecure: Allow "insecure" SSL connections and transfers
            offline: Offline mode, don't connect to the Internet
            dry_run: Only display what would have been done
            yes: Do not ask for confirmation
            quiet: Do not display progress bar
            as_json: Report all output as json
            verbose: Show additional output details
            console: Select the backend for output rendering
            download_only: Solve environment and populate caches but don't install
            file: Read package versions from the given file

        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["update"]
        
        # Handle environment specification
        if name:
            args.extend(["-n", name])
        if prefix:
            args.extend(["-p", prefix])
            
        # Handle package specs and sources
        if packages:
            args.extend(packages)
        if file:
            args.extend(["--file", file])
            
        # Handle channels
        if channels:
            for channel in channels:
                args.extend(["-c", channel])
        if use_local:
            args.append("--use-local")
        if override_channels:
            args.append("--override-channels")
        if repodata_fn:
            for fn in repodata_fn:
                args.extend(["--repodata-fn", fn])
        if experimental:
            args.extend(["--experimental", experimental])
        if no_lock:
            args.append("--no-lock")
        if repodata_use_zst is not None:
            args.append("--repodata-use-zst" if repodata_use_zst else "--no-repodata-use-zst")
            
        # Handle solver options
        if strict_channel_priority:
            args.append("--strict-channel-priority")
        if no_channel_priority:
            args.append("--no-channel-priority")
        if no_deps:
            args.append("--no-deps")
        if only_deps:
            args.append("--only-deps")
        if no_pin:
            args.append("--no-pin")
        if solver:
            args.extend(["--solver", solver])
        if force_reinstall:
            args.append("--force-reinstall")
        if freeze_installed:
            args.append("--freeze-installed")
        if update_deps:
            args.append("--update-deps")
        if satisfied_skip_solve:
            args.append("-S")
        if update_all:
            args.append("--update-all")
        if update_specs:
            args.append("--update-specs")
            
        # Handle package linking options
        if copy:
            args.append("--copy")
        if no_shortcuts:
            args.append("--no-shortcuts")
        if shortcuts_only:
            for pkg in shortcuts_only:
                args.extend(["--shortcuts-only", pkg])
        if clobber:
            args.append("--clobber")
                
        # Handle networking options
        if use_index_cache:
            args.append("-C")
        if insecure:
            args.append("-k")
        if offline:
            args.append("--offline")
            
        # Handle output options
        if dry_run:
            args.append("-d")
        if yes:
            args.append("-y")
        if as_json:
            args.append("--json")
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")
        if console:
            args.extend(["--console", console])
        if download_only:
            args.append("--download-only")
        if show_channel_urls:
            args.append("--show-channel-urls")

        return await self.fork(self.binary_path, args)

    async def list(
        self,
        name: Optional[str] = None,
        prefix: Optional[str] = None,
        regex: Optional[str] = None,
        show_channel_urls: bool = False,
        reverse: bool = False,
        canonical: bool = False,
        full_name: bool = False,
        explicit: bool = False,
        md5: bool = False,
        sha256: bool = False,
        export: bool = False,
        revisions: bool = False,
        no_pip: bool = False,
        auth: bool = False,
        as_json: bool = False,
        verbose: bool = False,
        quiet: bool = False,
    ):
        """List installed packages in a conda environment.

        This tool displays all packages installed in the specified (or current) conda environment.
        It supports various output formats and filtering options.

        Args:
            name: Name of environment
            prefix: Full path to environment location (i.e. prefix)
            regex: List only packages matching this regular expression
            show_channel_urls: Show channel urls
            reverse: List installed packages in reverse order
            canonical: Output canonical names of packages only
            full_name: Only search for full names, i.e., ^<regex>$
            explicit: List explicitly all installed conda packages with URL
            md5: Add MD5 hashsum when using --explicit
            sha256: Add SHA256 hashsum when using --explicit
            export: Output requirement strings instead of human-readable lists
            revisions: List the revision history
            no_pip: Do not include pip-only installed packages
            auth: In explicit mode, leave authentication details in package URLs
            as_json: Report all output as json
            verbose: Show additional output details
            quiet: Do not display progress bar

        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["list"]
        
        # Handle environment specification
        if name:
            args.extend(["-n", name])
        if prefix:
            args.extend(["-p", prefix])
            
        # Handle filtering and formatting
        if regex:
            args.append(regex)
        if show_channel_urls:
            args.append("--show-channel-urls")
        if reverse:
            args.append("--reverse")
        if canonical:
            args.append("--canonical")
        if full_name:
            args.append("--full-name")
        if explicit:
            args.append("--explicit")
        if md5:
            args.append("--md5")
        if sha256:
            args.append("--sha256")
        if export:
            args.append("--export")
        if revisions:
            args.append("--revisions")
        if no_pip:
            args.append("--no-pip")
        if auth:
            args.append("--auth")
            
        # Handle output options
        if as_json:
            args.append("--json")
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")
            
        return await self.fork(self.binary_path, args)
    
    async def run(
        self,
        executable_call: List[str],
        name: Optional[str] = None,
        prefix: Optional[str] = None,
        verbose: bool = False,
        dev: bool = False,
        debug_wrapper_scripts: bool = False,
        cwd: Optional[str] = None,
        no_capture_output: bool = False,
        status_callback: Optional[Callable] = None
    ):
        """Run an executable in a conda environment.

        This tool allows running commands or executables within a specific conda environment.
        The command is executed asynchronously and its output is tracked.

        Args:
            executable_call: List containing executable name and any additional arguments
            name: Name of environment
            prefix: Full path to environment location (i.e. prefix)
            verbose: Show additional output details
            dev: Use sys.executable -m conda in wrapper scripts
            debug_wrapper_scripts: Print debugging information to stderr
            cwd: Current working directory for command execution
            no_capture_output: Don't capture stdout/stderr (live stream)
            status_callback: Optional callback for process status updates

        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["run"]
        
        # Handle environment specification
        if name:
            args.extend(["-n", name])
        if prefix:
            args.extend(["-p", prefix])
            
        # Handle options
        if verbose:
            args.append("-v")
        if dev:
            args.append("--dev")
        if debug_wrapper_scripts:
            args.append("--debug-wrapper-scripts")
        if cwd:
            args.extend(["--cwd", cwd])
        if no_capture_output:
            args.append("--no-capture-output")
            
        # Add executable and its arguments
        args.extend(executable_call)
            
        return await self.fork(self.binary_path, args)

    async def install(
        self,
        name: Optional[str] = None,
        prefix: Optional[str] = None,
        packages: Optional[List[str]] = None,
        revision: Optional[str] = None,
        file: Optional[str] = None,
        channels: Optional[List[str]] = None,
        use_local: bool = False,
        override_channels: bool = False,
        repodata_fn: Optional[List[str]] = None,
        experimental: Optional[str] = None,
        no_lock: bool = False,
        repodata_use_zst: Optional[bool] = None,
        strict_channel_priority: bool = False,
        no_channel_priority: bool = False,
        no_deps: bool = False,
        only_deps: bool = False,
        no_pin: bool = False,
        solver: Optional[str] = None,
        force_reinstall: bool = False,
        freeze_installed: bool = False,
        update_deps: bool = False,
        satisfied_skip_solve: bool = False,
        update_all: bool = False,
        update_specs: bool = False,
        copy: bool = False,
        no_shortcuts: bool = False,
        shortcuts_only: Optional[List[str]] = None,
        clobber: bool = False,
        use_index_cache: bool = False,
        insecure: bool = False,
        offline: bool = False,
        dry_run: bool = False,
        yes: bool = True,
        quiet: bool = False,
        as_json: bool = False,
        verbose: bool = False,
        console: Optional[str] = None,
        download_only: bool = False,
        show_channel_urls: bool = False,
        dev: bool = False,
    ):
        """Install a list of packages into a specified conda environment.

        This tool installs packages into a conda environment based on package specifications.
        It ensures compatibility between packages and handles dependencies appropriately.

        Args:
            name: Name of environment
            prefix: Full path to environment location (i.e. prefix)
            packages: List of packages to install or update
            revision: Revert to the specified REVISION
            file: Read package versions from the given file
            channels: Additional channels to search for packages
            use_local: Use locally built packages (identical to '-c local')
            override_channels: Do not search default or .condarc channels
            repodata_fn: Specify file names of repodata on remote server
            experimental: Enable experimental features ('jlap' or 'lock')
            no_lock: Disable locking when reading/updating index cache
            repodata_use_zst: Check for repodata.json.zst
            strict_channel_priority: Packages in lower priority channels are not considered
            no_channel_priority: Package version takes precedence over channel priority
            no_deps: Do not install dependencies
            only_deps: Only install dependencies
            no_pin: Ignore pinned file
            solver: Choose solver backend ('classic' or 'libmamba')
            force_reinstall: Ensure that any user-requested package is reinstalled
            freeze_installed: Do not update or change already-installed dependencies
            update_deps: Update dependencies that have available updates
            satisfied_skip_solve: Exit early if the requested specs are satisfied
            update_all: Update all installed packages in the environment
            update_specs: Update based on provided specifications
            copy: Install all packages using copies instead of hard- or soft-linking
            no_shortcuts: Don't install start menu shortcuts
            shortcuts_only: Install shortcuts only for specified packages
            clobber: Allow clobbering of overlapping file paths within packages
            use_index_cache: Use cache of channel index files even if expired
            insecure: Allow "insecure" SSL connections and transfers
            offline: Offline mode, don't connect to the Internet
            dry_run: Only display what would have been done
            yes: Do not ask for confirmation
            quiet: Do not display progress bar
            as_json: Report all output as json
            verbose: Show additional output details
            console: Select the backend for output rendering
            download_only: Solve environment and populate caches but don't install
            show_channel_urls: Show channel urls
            dev: Use sys.executable -m conda in wrapper scripts

        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["install"]
        
        # Handle environment specification
        if name:
            args.extend(["-n", name])
        if prefix:
            args.extend(["-p", prefix])
            
        # Handle package specs and sources
        if packages:
            args.extend(packages)
        if revision:
            args.extend(["--revision", revision])
        if file:
            args.extend(["--file", file])
            
        # Handle channels
        if channels:
            for channel in channels:
                args.extend(["-c", channel])
        if use_local:
            args.append("--use-local")
        if override_channels:
            args.append("--override-channels")
        if repodata_fn:
            for fn in repodata_fn:
                args.extend(["--repodata-fn", fn])
        if experimental:
            args.extend(["--experimental", experimental])
        if no_lock:
            args.append("--no-lock")
        if repodata_use_zst is not None:
            args.append("--repodata-use-zst" if repodata_use_zst else "--no-repodata-use-zst")
            
        # Handle solver options
        if strict_channel_priority:
            args.append("--strict-channel-priority")
        if no_channel_priority:
            args.append("--no-channel-priority")
        if no_deps:
            args.append("--no-deps")
        if only_deps:
            args.append("--only-deps")
        if no_pin:
            args.append("--no-pin")
        if solver:
            args.extend(["--solver", solver])
        if force_reinstall:
            args.append("--force-reinstall")
        if freeze_installed:
            args.append("--freeze-installed")
        if update_deps:
            args.append("--update-deps")
        if satisfied_skip_solve:
            args.append("-S")
        if update_all:
            args.append("--update-all")
        if update_specs:
            args.append("--update-specs")
            
        # Handle package linking options
        if copy:
            args.append("--copy")
        if no_shortcuts:
            args.append("--no-shortcuts")
        if shortcuts_only:
            for pkg in shortcuts_only:
                args.extend(["--shortcuts-only", pkg])
        if clobber:
            args.append("--clobber")
                
        # Handle networking options
        if use_index_cache:
            args.append("-C")
        if insecure:
            args.append("-k")
        if offline:
            args.append("--offline")
            
        # Handle output options
        if dry_run:
            args.append("-d")
        if yes:
            args.append("-y")
        if as_json:
            args.append("--json")
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")
        if console:
            args.extend(["--console", console])
        if download_only:
            args.append("--download-only")
        if show_channel_urls:
            args.append("--show-channel-urls")
            
        # Handle development options
        if dev:
            args.append("--dev")
        
        return await self.fork(self.binary_path, args)


    async def compare(
        self,
        file: str,
        name: Optional[str] = None,
        prefix: Optional[str] = None,
        verbose: bool = False,
        quiet: bool = False,
        as_json: bool = False,
        console: Optional[str] = None,
    ) -> ProcessStatus:
        """Compare packages between conda environments.

        This tool compares packages in an environment against those specified in an environment file.
        It helps identify differences in package versions and specifications.

        Args:
            file: Path to the environment file to compare against
            name: Name of environment
            prefix: Full path to environment location (i.e. prefix)
            verbose: Show additional output details
            quiet: Do not display progress bar
            as_json: Report all output as json
            console: Select the backend for output rendering

        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["compare"]

        # Add environment file
        args.append(file)

        # Handle environment specification
        if name:
            args.extend(["-n", name])
        elif prefix:
            args.extend(["-p", prefix])

        # Handle output options
        if as_json:
            args.append("--json")
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")
        if console:
            args.extend(["--console", console])

        return await self.fork(self.binary_path, args)

    async def info(
        self,
        all: bool = False,
        base: bool = False,
        envs: bool = False,
        system: bool = False,
        unsafe_channels: bool = False,
        verbose: bool = False,
        quiet: bool = False,
        as_json: bool = False,
    ) -> Union[ProcessStatus, Tuple[ProcessStatus, Dict]]:
        """Display information about current conda install.

        This tool provides detailed information about the conda installation and environments.
        It can show various aspects of the installation including environment paths, system variables,
        and channel configurations.

        Args:
            all: Show all information
            base: Show base environment path
            envs: List all known conda environments
            system: List environment variables
            unsafe_channels: Show unsafe channels
            verbose: Show additional output details
            quiet: Do not display progress bar
            as_json: Report all output as json

        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["info"]
        
        # Handle info targets
        if all:
            args.append("--all")
        if base:
            args.append("--base")
        if envs:
            args.append("--envs")
        if system:
            args.append("--system")
        if unsafe_channels:
            args.append("--unsafe-channels")
            
        # Handle output options
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")
        if as_json:
            args.append("--json")

        return await self.fork(self.binary_path, args)

    async def search(
        self,
        query: Optional[str] = None,
        envs: bool = False,
        info: bool = False,
        subdir: Optional[str] = None,
        skip_flexible_search: bool = False,
        channels: Optional[List[str]] = None,
        use_local: bool = False,
        override_channels: bool = False,
        repodata_fn: Optional[List[str]] = None,
        experimental: Optional[str] = None,
        no_lock: bool = False,
        repodata_use_zst: Optional[bool] = None,
        insecure: bool = False,
        offline: bool = False,
        verbose: bool = False,
        quiet: bool = False,
        as_json: bool = False,
        use_index_cache: bool = False,
    ) -> Union[ProcessStatus, Tuple[ProcessStatus, Dict]]:
        """Search for conda packages using the MatchSpec format.

        This tool searches for packages in conda channels using flexible matching.
        It can search in all environments and provide detailed package information.

        Args:
            query: Search query in MatchSpec format
            envs: Search all conda environments
            info: Provide detailed information about each package
            subdir: Search the given subdir
            skip_flexible_search: Skip flexible search (exact match only)
            channels: Additional channels to search
            use_local: Use locally built packages
            override_channels: Override default channels
            repodata_fn: Specify file names of repodata on remote server
            experimental: Enable experimental features ('jlap' or 'lock')
            no_lock: Disable locking when reading/updating index cache
            repodata_use_zst: Check for repodata.json.zst
            insecure: Allow "insecure" SSL connections and transfers
            offline: Work offline (no network access)
            verbose: Show additional output details
            quiet: Do not display progress bar
            as_json: Report all output as json
            use_index_cache: Use cache of channel index files even if expired

        Returns:
            ProcessStatus object for tracking the command execution. The caller can use
            get_command_status(pid) to check status and get_command_log(pid) to retrieve the raw
            command output.
        """
        args = ["search"]
        
        # Add search query if provided
        if query:
            args.append(query)
            
        # Handle search options
        if envs:
            args.append("--envs")
        if info:
            args.append("--info")
        if subdir:
            args.extend(["--subdir", subdir])
        if skip_flexible_search:
            args.append("--skip-flexible-search")
            
        # Handle channel options
        if channels:
            for channel in channels:
                args.extend(["-c", channel])
        if use_local:
            args.append("--use-local")
        if override_channels:
            args.append("--override-channels")
            
        # Handle repodata options
        if repodata_fn:
            for fn in repodata_fn:
                args.extend(["--repodata-fn", fn])
        if experimental:
            args.extend(["--experimental", experimental])
        if no_lock:
            args.append("--no-lock")
        if repodata_use_zst is not None:
            args.append("--repodata-use-zst" if repodata_use_zst else "--no-repodata-use-zst")
            
        # Handle networking options
        if offline:
            args.append("--offline")
        if use_index_cache:
            args.append("-C")
        if insecure:
            args.append("-k")
            
        # Handle output options
        if verbose:
            args.append("-v")
        if quiet:
            args.append("-q")
        if as_json:
            args.append("--json")

        return await self.fork(self.binary_path, args)
