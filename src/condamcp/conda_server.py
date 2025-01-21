from mcp.server.fastmcp import FastMCP, Context
from .condacmd import Condacmd, AsyncCondaCmd, ProcessStatus
import json
import asyncio
from typing import Union, Tuple, Any, List, Optional, Callable, Dict

mcp = FastMCP("Conda")
conda = Condacmd(use_shell=True)
async_conda = AsyncCondaCmd()

def _handle_json_output(result: Union[Tuple[int, str, str], str], indent: int = 2) -> str:
    """Handle JSON output from conda commands.
    
    This function handles string or tuple output from conda commands and
    returns a properly formatted JSON string.
    
    Args:
        result: The result from a conda command, which could be:
               - A tuple of (returncode, stdout, stderr)
               - A string containing JSON data
        indent: Number of spaces for JSON indentation
               
    Returns:
        A properly formatted JSON string
        
    Raises:
        Exception: If the result cannot be parsed as JSON
    """
    try:
        # Handle tuple (returncode, stdout, stderr)
        if isinstance(result, tuple):
            _, json_result = result
            try:
                # Try to parse the string output as JSON
                parsed = json.loads(json_result)
                return json.dumps(parsed, indent=indent)
            except json.JSONDecodeError:
                raise Exception("Invalid JSON response from conda command")
                
        # Handle string
        if isinstance(result, str):
            try:
                # Try to parse string as JSON
                parsed = json.loads(result)
                return json.dumps(parsed, indent=indent)
            except json.JSONDecodeError:
                raise Exception("Invalid JSON response from conda command")
                
        raise Exception("Unexpected result format from conda command")
        
    except Exception as e:
        if not str(e).startswith("Invalid JSON"):
            raise Exception(f"Error processing JSON output: {str(e)}")
        raise

def _create_status_callback(
    ctx: Context, 
    command: str, 
    output_lines: List[str], 
    error_lines: List[str]) -> Callable[[ProcessStatus], None]:
    """Create a status callback function for conda commands.
    
    Args:
        ctx: MCP context for providing progress updates
        command: The conda command being run (for progress messages)
        output_lines: List to accumulate stdout lines
        error_lines: List to accumulate stderr lines
        
    Returns:
        A callback function that handles ProcessStatus updates
    """
    last_update = 0  # Track last status update time
    
    def callback(status: ProcessStatus):
        nonlocal last_update
        current_time = asyncio.get_event_loop().time()
        
        if status.stdout:
            line = status.stdout.strip()
            output_lines.append(status.stdout)
            
            # Send periodic update every 1 second
            if current_time - last_update >= 1:
                ctx.info(f"Running conda {command}...")
                last_update = current_time
                
        if status.stderr:
            error_lines.append(status.stderr)
            ctx.error(status.stderr.rstrip())  # Only show errors in context
            
    return callback

@mcp.tool()
async def env(
    ctx: Context,
    command: str,
    args: Optional[List[str]] = None,
    as_json: bool = False,
    verbose: bool = False,
    quiet: bool = False
) -> str:
    """Execute a conda environment command.

    This tool provides direct access to conda environment commands like list, create,
    remove, export, update, and config.

    Args:
        ctx: MCP context for providing progress updates
        command: The environment subcommand to run (e.g. "list", "create", "remove", "export", "update", "config")
        args: Additional arguments to pass to the command
        as_json: Return output as JSON
        verbose: Show additional output details
        quiet: Minimize output (suppress progress bars)

    Returns:
        A string containing either:
        - The command output in text format (default)
        - A JSON string with command output (if as_json=True)

    Examples:
        "List all environments" (command="list")
        "Create environment from environment.yml" (command="create", args=["-f", "environment.yml"])
        "Remove environment myenv" (command="remove", args=["-n", "myenv"])
        "Export environment to file" (command="export", args=["-n", "myenv", "-f", "env.yml"])
    """
    try:
        ctx.info(f"Running conda env {command}...")
        await ctx.report_progress(0, 2)

        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, f"env {command}", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda env command
        cmd_args = args if args else []
        status = await async_conda.env(
            command,
            *cmd_args,
            as_json=as_json,
            verbose=verbose,
            quiet=quiet,
            status_callback=callback
        )

        await ctx.report_progress(2, 2)
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to run conda env {command}: {error_msg}")
            raise Exception(f"Failed to run conda env {command}: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        return f"Conda env {command} completed successfully"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def create(
    ctx: Context,
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
    dev: bool = False
) -> str:
    """Create a new conda environment from a list of specified packages.

    To use the newly-created environment, use 'conda activate envname'.
    This command requires either the -n NAME or -p PREFIX option.

    Args:
        ctx: MCP context for providing progress updates
        name: Name of environment
        prefix: Full path to environment location (i.e. prefix)
        packages: List of packages to install in the environment
        clone: Create a new environment as a copy of an existing local environment
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
        no_default_packages: Ignore create_default_packages in .condarc
        copy: Install all packages using copies instead of hard- or soft-linking
        no_shortcuts: Don't install start menu shortcuts
        shortcuts_only: Install shortcuts only for specified packages
        use_index_cache: Use cache of channel index files even if expired
        insecure: Allow "insecure" SSL connections and transfers
        offline: Offline mode, don't connect to the Internet
        solver: Choose solver backend ('classic' or 'libmamba')
        dry_run: Only display what would have been done
        yes: Do not ask for confirmation
        quiet: Do not display progress bar
        as_json: Report all output as json
        verbose: Show additional output details
        console: Select the backend for output rendering
        download_only: Solve environment and populate caches but don't install
        show_channel_urls: Show channel urls
        subdir: Use packages built for this platform
        dev: Use sys.executable -m conda in wrapper scripts

    Returns:
        A string containing either:
        - The command output in text format (default)
        - A JSON string with command output (if as_json=True)

    Examples:
        "Create an environment with sqlite"
        "Clone an existing environment"
    """
    try:
        if name:
            ctx.info(f"Creating conda environment '{name}'...")
        elif prefix:
            ctx.info(f"Creating conda environment at '{prefix}'...")
        else:
            ctx.info("Creating conda environment...")
        await ctx.report_progress(0, 2)
        
        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "create", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda create command
        status = await async_conda.create(
            name=name,
            prefix=prefix,
            packages=packages,
            clone=clone,
            file=file,
            channels=channels,
            use_local=use_local,
            override_channels=override_channels,
            repodata_fn=repodata_fn,
            experimental=experimental,
            no_lock=no_lock,
            repodata_use_zst=repodata_use_zst,
            strict_channel_priority=strict_channel_priority,
            no_channel_priority=no_channel_priority,
            no_deps=no_deps,
            only_deps=only_deps,
            no_pin=no_pin,
            no_default_packages=no_default_packages,
            copy=copy,
            no_shortcuts=no_shortcuts,
            shortcuts_only=shortcuts_only,
            use_index_cache=use_index_cache,
            insecure=insecure,
            offline=offline,
            solver=solver,
            dry_run=dry_run,
            yes=yes,
            quiet=quiet,
            as_json=as_json,
            verbose=verbose,
            console=console,
            download_only=download_only,
            show_channel_urls=show_channel_urls,
            subdir=subdir,
            dev=dev,
            status_callback=callback
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to create environment: {error_msg}")
            raise Exception(f"Failed to create environment: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        return "Environment created successfully"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def remove(
    ctx: Context,
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
    dev: bool = False
) -> str:
    """Remove packages from a conda environment.

    This tool removes packages from the specified (or current) conda environment.
    It can also remove all packages or the entire environment if requested.

    Args:
        ctx: MCP context for providing progress updates
        name: Name of environment
        prefix: Full path to environment location (i.e. prefix)
        packages: Package names to remove from the environment
        all: Remove all packages, i.e., the entire environment
        keep_env: Used with `--all`, delete all packages but keep the environment
        channels: Additional channels to search for packages
        use_local: Use locally built packages (identical to '-c local')
        override_channels: Do not search default or .condarc channels
        repodata_fn: Specify file names of repodata on remote server
        experimental: Enable experimental features ('jlap' or 'lock')
        no_lock: Disable locking when reading/updating index cache
        repodata_use_zst: Check for repodata.json.zst
        features: Remove features (instead of packages)
        force_remove: Forces removal without removing dependent packages
        no_pin: Ignore pinned package(s)
        solver: Choose solver backend ('classic' or 'libmamba')
        use_index_cache: Use cache of channel index files even if expired
        insecure: Allow "insecure" SSL connections and transfers
        offline: Offline mode, don't connect to the Internet
        dry_run: Only display what would have been done
        yes: Do not ask for confirmation
        quiet: Do not display progress bar
        as_json: Report all output as json
        verbose: Use multiple times for more detailed output
        console: Select the backend for output rendering
        dev: Use sys.executable -m conda in wrapper scripts

    Returns:
        A string containing either:
        - The command output in text format (default)
        - A JSON string with command output (if as_json=True)

    Examples:
        "Remove package from current environment"
        "Remove packages from specific environment"
        "Remove all packages and the environment"
        "Remove all packages but keep the environment"
    """
    try:
        if name:
            ctx.info(f"Removing packages from environment '{name}'...")
        elif prefix:
            ctx.info(f"Removing packages from environment at '{prefix}'...")
        else:
            ctx.info("Removing packages from current environment...")
        await ctx.report_progress(0, 2)
        
        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "remove", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda remove command
        status = await async_conda.remove(
            name=name,
            prefix=prefix,
            packages=packages,
            all=all,
            keep_env=keep_env,
            channels=channels,
            use_local=use_local,
            override_channels=override_channels,
            repodata_fn=repodata_fn,
            experimental=experimental,
            no_lock=no_lock,
            repodata_use_zst=repodata_use_zst,
            features=features,
            force_remove=force_remove,
            no_pin=no_pin,
            solver=solver,
            use_index_cache=use_index_cache,
            insecure=insecure,
            offline=offline,
            dry_run=dry_run,
            yes=yes,
            quiet=quiet,
            as_json=as_json,
            verbose=verbose,
            console=console,
            dev=dev,
            status_callback=callback
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to remove packages: {error_msg}")
            raise Exception(f"Failed to remove packages: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        # Return appropriate success message
        if all and not keep_env:
            return f"Environment '{name}' removed successfully"
        elif all:
            return f"All packages removed from environment '{name}'"
        elif packages:
            return f"Packages {', '.join(packages)} removed successfully"
        else:
            return "Removal completed successfully"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def help(command: Optional[str] = None) -> str:
    """Show help information for conda commands.

    This tool displays help information for conda commands and subcommands.

    Args:
        command: The conda command to show help for (e.g., "build", "env create")
                If not provided, shows general conda help.

    Returns:
        str: Help text output

    Examples:
        "Show conda help"
        "Show help for conda build"
        "Show help for conda env create"
        "What are the options for conda build?"
    """
    # Accumulate output for proper handling
    output_lines = []
    error_lines = []
    
    # Create callback to accumulate output
    def callback(status: ProcessStatus):
        if status.stdout:
            output_lines.append(status.stdout)
        if status.stderr:
            error_lines.append(status.stderr)
    
    # Run the conda help command
    status = await async_conda.help(command, status_callback=callback)
    
    # Handle errors
    if error_lines and not output_lines:
        error_msg = "\n".join(error_lines)
        raise Exception(f"Failed to get help: {error_msg}")
    
    # Return accumulated output
    if output_lines:
        return "\n".join(output_lines)
    
    return status.stdout if status.stdout else status.stderr

@mcp.tool()
async def list(
    ctx: Context,
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
    quiet: bool = False
) -> str:
    """List installed packages in a conda environment.

    This tool displays all packages installed in the specified (or current) conda environment.
    It supports various output formats and filtering options.

    Args:
        ctx: MCP context for providing progress updates
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
        A string containing either:
        - A formatted list of installed packages (default)
        - A JSON string with package details (if as_json=True)
        - An export format suitable for conda create --file (if export=True)
        - A list of revisions (if revisions=True)

    Examples:
        "List all packages in current environment"
        "Show packages in environment myenv"
        "List python packages in current environment"
        "Export package list for environment myenv"
        "Show installed packages with their channels"
        "List with explicit URLs and SHA256 hashes"
    """
    try:
        if name:
            ctx.info(f"Listing packages in environment '{name}'...")
        elif prefix:
            ctx.info(f"Listing packages in environment at '{prefix}'...")
        else:
            ctx.info("Listing packages in current environment...")
        await ctx.report_progress(0, 2)

        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "list", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda list command
        status = await async_conda.list(
            name=name,
            prefix=prefix,
            regex=regex,
            show_channel_urls=show_channel_urls,
            reverse=reverse,
            canonical=canonical,
            full_name=full_name,
            explicit=explicit,
            md5=md5,
            sha256=sha256,
            export=export,
            revisions=revisions,
            no_pip=no_pip,
            auth=auth,
            as_json=as_json,
            verbose=verbose,
            quiet=quiet,
            status_callback=callback
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to list packages: {error_msg}")
            raise Exception(f"Failed to list packages: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        return "No packages found"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def clean(
    ctx: Context,
    all: bool = False,
    index_cache: bool = False,
    packages: bool = False,
    tarballs: bool = False,
    force_pkgs_dirs: bool = False,
    tempfiles: Optional[List[str]] = None,
    logfiles: bool = False,
    dry_run: bool = False,
    yes: bool = True,
    quiet: bool = True,
    as_json: bool = False,
    verbose: bool = False,
    console: Optional[str] = None
) -> str:
    """Remove unused packages and caches.

    This tool removes unused conda packages and caches to free up disk space.
    It can clean various types of conda caches and temporary files.

    Args:
        ctx: MCP context for providing progress updates
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

    Returns:
        A string containing either:
        - The command output in text format (default)
        - A JSON string with command output (if as_json=True)

    Examples:
        "Clean all caches"
        "Remove only tarballs"
        "Clean index cache and packages"
    """
    try:
        ctx.info("Cleaning conda caches...")
        await ctx.report_progress(0, 2)

        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "clean", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda clean command
        status = await async_conda.clean(
            all=all,
            index_cache=index_cache,
            packages=packages,
            tarballs=tarballs,
            force_pkgs_dirs=force_pkgs_dirs,
            tempfiles=tempfiles,
            logfiles=logfiles,
            dry_run=dry_run,
            yes=yes,
            quiet=quiet,
            as_json=as_json,
            verbose=verbose,
            console=console,
            status_callback=callback
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to clean caches: {error_msg}")
            raise Exception(f"Failed to clean caches: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        # Return simple success message if no output
        return "Clean completed successfully"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def compare(
    ctx: Context,
    file: str,
    name: Optional[str] = None,
    prefix: Optional[str] = None,
    verbose: bool = False,
    quiet: bool = False,
    as_json: bool = False,
    console: Optional[str] = None
) -> str:
    """Compare packages between conda environments.

    This tool compares packages in an environment against those specified in an environment file.
    It helps identify differences in package versions and specifications. Use conda export to 
    create an environment file.

    Args:
        ctx: MCP context for providing progress updates
        file: Path to the environment file to compare against
        name: Name of environment to compare (None for current environment)
        prefix: Full path to environment location (i.e. prefix)
        verbose: Show additional comparison details
        quiet: Do not display progress bar
        as_json: Report all output as json
        console: Select the backend for output rendering

    Returns:
        A string containing either:
        - The comparison output in text format (default)
        - A JSON string with comparison details (if as_json=True)
        If no differences are found, returns an appropriate message.

    Examples:
        "export environments A and B to yaml files and run conda compare"
        "Compare current environment with environment.yml"
        "Compare environment myenv with path/to/environment.yml"
        "Show detailed comparison with environment.yml"
    """
    try:
        if name:
            ctx.info(f"Comparing environment '{name}' with '{file}'...")
        elif prefix:
            ctx.info(f"Comparing environment at '{prefix}' with '{file}'...")
        else:
            ctx.info(f"Comparing current environment with '{file}'...")
        await ctx.report_progress(0, 2)

        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "compare", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda compare command
        status = await async_conda.compare(
            file=file,
            name=name,
            prefix=prefix,
            verbose=verbose,
            quiet=quiet,
            as_json=as_json,
            console=console,
            status_callback=callback
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # For compare command, return code 1 means differences were found (expected behavior)
        if status.return_code not in (0, 1):
            error_msg = "\n".join(error_lines) if error_lines else status.stderr
            ctx.error(f"Failed to compare environments: {error_msg}")
            raise Exception(f"Failed to compare environments: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return accumulated output if available
        if output_lines:
            return "\n".join(output_lines)
        
        # If no output but command succeeded, environments are identical
        if status.return_code == 0:
            return "No differences found between environments"
        
        # If no output but differences found (return code 1), return status output
        return status.stdout if status.stdout else "Differences found between environments (no details available)"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def info(
    ctx: Context,
    all: bool = False,
    base: bool = False,
    envs: bool = False,
    system: bool = False,
    unsafe_channels: bool = False,
    verbose: bool = False,
    quiet: bool = False,
    as_json: bool = False
) -> str:
    """Display information about current conda install.

    This tool provides detailed information about the conda installation and environments.

    Args:
        ctx: MCP context for providing progress updates
        all: Show all information
        base: Show base environment path
        envs: List all known conda environments
        system: List environment variables
        unsafe_channels: Show unsafe channels
        verbose: Show additional output details
        quiet: Do not display progress bar
        as_json: Report all output as json

    Returns:
        A string containing either:
        - The conda information in text format (default)
        - A JSON string with detailed information (if as_json=True)

    Examples:
        "Show all conda information"
        "List all conda environments"
        "Show conda base environment path"
        "Display system environment variables"
    """
    try:
        ctx.info("Getting conda information...")
        await ctx.report_progress(0, 2)

        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "info", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda info command
        status = await async_conda.info(
            all=all,
            base=base,
            envs=envs,
            system=system,
            unsafe_channels=unsafe_channels,
            verbose=verbose,
            quiet=quiet,
            as_json=as_json,
            status_callback=callback
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to get conda info: {error_msg}")
            raise Exception(f"Failed to get conda info: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        return status.stdout if status.stdout else "No information available"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def search(
    ctx: Context,
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
    use_index_cache: bool = False
) -> str:
    """Search for conda packages using the MatchSpec format.

    This tool searches for packages in conda channels using flexible matching.
    It can search in all environments and provide detailed package information.

    Args:
        ctx: MCP context for providing progress updates
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
        A string containing either:
        - A formatted list of packages (default)
        - A JSON string with package details (if as_json=True)

    Examples:
        "Search for numpy packages"
        "Find all versions of python"
        "Search for scipy in conda-forge channel"
        "Show detailed info about matplotlib"
        "List all packages in all environments"
    """
    try:
        if query:
            ctx.info(f"Searching for packages matching '{query}'...")
        else:
            ctx.info("Searching for packages...")
        await ctx.report_progress(0, 2)

        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "search", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda search command
        status = await async_conda.search(
            query=query,
            envs=envs,
            info=info,
            subdir=subdir,
            skip_flexible_search=skip_flexible_search,
            channels=channels,
            use_local=use_local,
            override_channels=override_channels,
            repodata_fn=repodata_fn,
            experimental=experimental,
            no_lock=no_lock,
            repodata_use_zst=repodata_use_zst,
            insecure=insecure,
            offline=offline,
            verbose=verbose,
            quiet=quiet,
            as_json=as_json,
            use_index_cache=use_index_cache,
            status_callback=callback
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to search packages: {error_msg}")
            raise Exception(f"Failed to search packages: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        return status.stdout if status.stdout else "No packages found matching the criteria"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def run_in_background(
    ctx: Context,
    executable_call: List[str],
    name: Optional[str] = None,
    prefix: Optional[str] = None,
    verbose: bool = False,
    dev: bool = False,
    debug_wrapper_scripts: bool = False,
    cwd: Optional[str] = None,
    no_capture_output: bool = False
) -> str:
    """Run an executable in a conda environment in the background.
    
    Similar to run() but returns immediately without waiting for completion.
    Output is logged to files but not captured in memory.
    
    Args:
        ctx: MCP context for providing progress updates
        executable_call: List containing executable name and any additional arguments
        name: Name of environment
        prefix: Full path to environment location (i.e. prefix)
        verbose: Show additional output details
        dev: Use sys.executable -m conda in wrapper scripts
        debug_wrapper_scripts: Print debugging information to stderr
        cwd: Current working directory for command execution
        no_capture_output: Don't capture stdout/stderr (live stream)
        
    Returns:
        A string indicating the command was started in the background including the PID
        
    Examples:
        "Run jupyter notebook server in background"
        "Start a long-running script in environment myenv"
    """
    try:
        if name:
            ctx.info(f"Starting background command in environment '{name}'...")
        elif prefix:
            ctx.info(f"Starting background command in environment at '{prefix}'...")
        else:
            ctx.info("Starting background command in current environment...")
        await ctx.report_progress(0, 2)

        # Run the conda run command in background
        status = await async_conda.run_in_background(
            executable_call=executable_call,
            name=name,
            prefix=prefix,
            verbose=verbose,
            dev=dev,
            debug_wrapper_scripts=debug_wrapper_scripts,
            cwd=cwd,
            no_capture_output=no_capture_output
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # Return success message with PID
        if status.pid:
            return f"Command started in background with PID {status.pid}"
        
        return "Command started in background"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def run(
    ctx: Context,
    executable_call: List[str],
    name: Optional[str] = None,
    prefix: Optional[str] = None,
    verbose: bool = False,
    dev: bool = False,
    debug_wrapper_scripts: bool = False,
    cwd: Optional[str] = None,
    no_capture_output: bool = False
) -> str:
    """Run an executable in a conda environment.

    This tool allows running commands or executables within a specific conda
    environment, with optional arguments and working directory specification. 
    If the command is long-running or blocking, use run_in_background instead.

    Args:
        ctx: MCP context for providing progress updates
        executable_call: List containing executable name and any additional arguments
        name: Name of environment
        prefix: Full path to environment location (i.e. prefix)
        verbose: Show additional output details
        dev: Use sys.executable -m conda in wrapper scripts
        debug_wrapper_scripts: Print debugging information to stderr
        cwd: Current working directory for command execution
        no_capture_output: Don't capture stdout/stderr (live stream)

    Returns:
        A string containing the command output or error message

    Examples:
        "Run python --version in environment myenv"
        "Execute script.py with arguments in environment py39"
        "Run jupyter notebook in data-science-env"
    """
    try:
        if name:
            ctx.info(f"Running command in environment '{name}'...")
        elif prefix:
            ctx.info(f"Running command in environment at '{prefix}'...")
        else:
            ctx.info("Running command in current environment...")
        await ctx.report_progress(0, 2)

        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "run", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda run command
        status = await async_conda.run(
            executable_call=executable_call,
            name=name,
            prefix=prefix,
            verbose=verbose,
            dev=dev,
            debug_wrapper_scripts=debug_wrapper_scripts,
            cwd=cwd,
            no_capture_output=no_capture_output,
            status_callback=callback
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to run command: {error_msg}")
            raise Exception(f"Failed to run command: {error_msg}")
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        return f"Command executed successfully"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def export(
    ctx: Context,
    name: Optional[str] = None,
    prefix: Optional[str] = None,
    file: Optional[str] = None,
    channels: Optional[List[str]] = None,
    override_channels: bool = False,
    no_builds: bool = False,
    ignore_channels: bool = False,
    from_history: bool = False,
    as_json: bool = False,
    verbose: bool = False,
    quiet: bool = False,
    console: Optional[str] = None
) -> str:
    """Export a given environment.

    This tool exports the specification of a conda environment, which can be used
    to recreate the environment on another system.

    Args:
        ctx: MCP context for providing progress updates
        name: Name of environment
        prefix: Full path to environment location (i.e. prefix)
        file: File name or path for the exported environment
        channels: Additional channels to include in the export
        override_channels: Do not include .condarc channels
        no_builds: Remove build specification from dependencies
        ignore_channels: Do not include channel names with package names
        from_history: Build environment spec from explicit specs in history
        as_json: Report all output as json
        verbose: Show additional output details
        quiet: Do not display progress bar
        console: Select the backend for output rendering

    Returns:
        A string containing either:
        - The environment specification in YAML format (default)
        - A JSON string with environment details (if as_json=True)

    Examples:
        "Export the current environment"
        "Export to a file"
    """
    try:
        if name:
            ctx.info(f"Exporting conda environment '{name}'...")
        elif prefix:
            ctx.info(f"Exporting conda environment at '{prefix}'...")
        else:
            ctx.info("Exporting current conda environment...")
        await ctx.report_progress(0, 2)

        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "export", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda export command
        status = await async_conda.export(
            name=name,
            prefix=prefix,
            file=file,
            channels=channels,
            override_channels=override_channels,
            no_builds=no_builds,
            ignore_channels=ignore_channels,
            from_history=from_history,
            as_json=as_json,
            console=console,
            verbose=verbose,
            quiet=quiet,
            status_callback=callback
        )

        await ctx.report_progress(2, 2)
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to export environment: {error_msg}")
            raise Exception(f"Failed to export environment: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        return "Environment exported successfully"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def install(
    ctx: Context,
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
    dev: bool = False
) -> str:
    """Install a list of packages into a specified conda environment.

    This command accepts a list of package specifications (e.g, bitarray=0.8)
    and installs a set of packages consistent with those specifications and
    compatible with the underlying environment.

    Args:
        ctx: MCP context for providing progress updates
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
        A string containing either:
        - The command output in text format (default)
        - A JSON string with command output (if as_json=True)

    Examples:
        "Install scipy in current environment"
        "Install packages in specific environment"
        "Install specific version of python"
    """
    try:
        if name:
            ctx.info(f"Installing packages in environment '{name}'...")
        elif prefix:
            ctx.info(f"Installing packages in environment at '{prefix}'...")
        else:
            ctx.info("Installing packages in current environment...")
        await ctx.report_progress(0, 2)

        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "install", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda install command
        status = await async_conda.install(
            name=name,
            prefix=prefix,
            packages=packages,
            revision=revision,
            file=file,
            channels=channels,
            use_local=use_local,
            override_channels=override_channels,
            repodata_fn=repodata_fn,
            experimental=experimental,
            no_lock=no_lock,
            repodata_use_zst=repodata_use_zst,
            strict_channel_priority=strict_channel_priority,
            no_channel_priority=no_channel_priority,
            no_deps=no_deps,
            only_deps=only_deps,
            no_pin=no_pin,
            solver=solver,
            force_reinstall=force_reinstall,
            freeze_installed=freeze_installed,
            update_deps=update_deps,
            satisfied_skip_solve=satisfied_skip_solve,
            update_all=update_all,
            update_specs=update_specs,
            copy=copy,
            no_shortcuts=no_shortcuts,
            shortcuts_only=shortcuts_only,
            clobber=clobber,
            use_index_cache=use_index_cache,
            insecure=insecure,
            offline=offline,
            dry_run=dry_run,
            yes=yes,
            quiet=quiet,
            as_json=as_json,
            verbose=verbose,
            console=console,
            download_only=download_only,
            show_channel_urls=show_channel_urls,
            dev=dev,
            status_callback=callback
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to install packages: {error_msg}")
            raise Exception(f"Failed to install packages: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        # Return appropriate success message
        if packages:
            return f"Packages {', '.join(packages)} installed successfully"
        elif update_all:
            return "All packages updated successfully"
        else:
            return "Installation completed successfully"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
async def upgrade(
    ctx: Context,
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
    file: Optional[str] = None
) -> str:
    """Update conda packages to the latest compatible version.

    This command accepts a list of package names and updates them to the latest
    versions that are compatible with all other packages in the environment.

    Conda attempts to install the newest versions of the requested packages. To
    accomplish this, it may update some packages that are already installed, or
    install additional packages. To prevent existing packages from updating,
    use the freeze_installed option. This may force conda to install older
    versions of the requested packages, and it does not prevent additional
    dependency packages from being installed.

    Args:
        ctx: MCP context for providing progress updates
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
        A string containing either:
        - The command output in text format (default)
        - A JSON string with command output (if as_json=True)

    Examples:
        "Update scipy in current environment"
        "Update all packages in environment myenv"
        "Update packages from requirements.txt"
        "Update with specific channel priority"
    """
    try:
        if name:
            ctx.info(f"Updating packages in environment '{name}'...")
        elif prefix:
            ctx.info(f"Updating packages in environment at '{prefix}'...")
        else:
            ctx.info("Updating packages in current environment...")
        await ctx.report_progress(0, 2)

        # Accumulate output for proper handling
        output_lines = []
        error_lines = []
        
        # Create callback with command name
        callback = _create_status_callback(ctx, "upgrade", output_lines, error_lines)

        await ctx.report_progress(1, 2)
        
        # Run the conda upgrade command
        status = await async_conda.upgrade(
            packages=packages,
            name=name,
            prefix=prefix,
            channels=channels,
            use_local=use_local,
            override_channels=override_channels,
            repodata_fn=repodata_fn,
            experimental=experimental,
            no_lock=no_lock,
            repodata_use_zst=repodata_use_zst,
            strict_channel_priority=strict_channel_priority,
            no_channel_priority=no_channel_priority,
            no_deps=no_deps,
            only_deps=only_deps,
            no_pin=no_pin,
            solver=solver,
            force_reinstall=force_reinstall,
            freeze_installed=freeze_installed,
            update_deps=update_deps,
            satisfied_skip_solve=satisfied_skip_solve,
            update_all=update_all,
            update_specs=update_specs,
            copy=copy,
            no_shortcuts=no_shortcuts,
            shortcuts_only=shortcuts_only,
            clobber=clobber,
            use_index_cache=use_index_cache,
            insecure=insecure,
            offline=offline,
            dry_run=dry_run,
            yes=yes,
            quiet=quiet,
            as_json=as_json,
            verbose=verbose,
            console=console,
            download_only=download_only,
            file=file,
            status_callback=callback
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        # Handle errors
        if error_lines and not output_lines:
            error_msg = "\n".join(error_lines)
            ctx.error(f"Failed to update packages: {error_msg}")
            raise Exception(f"Failed to update packages: {error_msg}")
        
        # Handle JSON output
        if as_json:
            try:
                # Join accumulated output and parse as JSON
                json_str = "".join(output_lines)
                try:
                    parsed = json.loads(json_str)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    # If parsing the joined output fails, try the status
                    return _handle_json_output(status)
            except Exception as e:
                ctx.error(str(e))
                raise
        
        # Return plain text output
        if output_lines:
            return "\n".join(output_lines)
        
        # Return appropriate success message
        if update_all:
            return "All packages updated successfully"
        elif packages:
            return f"Packages {', '.join(packages)} updated successfully"
        else:
            return "Update completed successfully"
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

def run_conda_server():
    """Entry point for the conda environment MCP server"""
    mcp.run()
