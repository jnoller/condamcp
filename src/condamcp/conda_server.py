from mcp.server.fastmcp import FastMCP, Context
from .condacmd import AsyncCondaCmd, ProcessStatus
import json
import asyncio
from typing import Union, Tuple, Any, List, Optional, Callable, Dict

mcp = FastMCP("Conda")
async_conda = AsyncCondaCmd(track_processes=True)

async def wait_for_command(pid, timeout_seconds=60):
    """ Shared function for tests to use to wait for a given process to finish 
    
    Args:
        pid: Process ID to wait for
        timeout_seconds: Maximum time to wait in seconds (default: 60)
    """
    iterations = int(timeout_seconds * 10)  # Convert seconds to iterations (0.1s sleep per iteration)
    for _ in range(iterations):
        proc_status = async_conda.get_process(pid)
        if proc_status['status'] in ['completed', 'failed']:
            break
        await asyncio.sleep(0.1)
    else:
        raise TimeoutError(f"Process {pid} did not complete within {timeout_seconds} seconds")

def get_command_output_as_json(pid: int) -> str:
    """Get the output of a command as JSON.
    
    Args:
        pid: Process ID of the command
        
    Returns:
        str: JSON string containing the command output
    """
    status = async_conda.get_process(pid)
    if status['status'] not in ['completed', 'failed']:
        raise Exception("Command is still running")
    return async_conda.get_json_response(pid)

@mcp.tool()
def cancel_command(pid: int):
    """Cancel a running conda command.
    
    Args:
        pid: Process ID of the command to cancel
    """
    try:
        async_conda.kill_process(pid)
        return f"Command {pid} cancelled successfully"
    except Exception as e:
        return f"Failed to cancel command {pid}: {e}"

@mcp.tool()
def get_command_status(
    ctx: Context,
    pid: int
) -> ProcessStatus:
    """Get the status of an executed conda command.
    
    Args:
        ctx: MCP context for providing progress updates
        pid: Process ID of the command that generated JSON output
        
    Returns:
        ProcessStatus: Status object tracking command execution, containing the command, args, 
        process ID, output / log file, return code and other relevant information for tracking
        the command's execution.

    Examples:
        "What is the status of the command with PID 1234567890?"
        "Check the status of my latest conda command"
        "What is the status of build 1234567890?"
    """
    ctx.info(f"Getting status of conda command with PID {pid}...")
    return async_conda.get_process(pid)

@mcp.tool()
def get_command_output(
    ctx: Context,
    pid: int,
    as_json: bool = False
) -> str:
    """Get the output of an executed conda command. If as_json is True, the output is 
    returned as a JSON string. Otherwise, the output is returned as a string. The command 
    that created the output must have been run with the `as_json` flag set to True.
    
    Args:
        ctx: MCP context for providing progress updates
        pid: Process ID of the command that generated JSON output
        as_json: Whether to return the output as a JSON string

    Returns:
        Text output from the command's log file, or a JSON string if as_json is True.
        If the command is still running, the function will return "Command is still running".

    Examples:
        "Show me the output of my latest conda command"
        "What is the output of build 1234567890?"
        "Get the output of command 1234567890 as JSON"
    """
    ctx.info(f"Getting output of conda command with PID {pid}...")
    # get the status of the command
    status = get_command_status(ctx, pid)
    # if the command is not finished, raise an exception
    if status['status']  not in ['completed', 'failed']:
        return "Command is still running"
    if as_json:
        return async_conda.get_json_response(pid)
    else:
        return async_conda.get_process_log(pid)

@mcp.tool()
async def list_environments(
    ctx: Context,
    as_json: bool = False
) -> str:
    """List all conda environments.
    
    This tool displays all available conda environments in the system.
    
    Args:
        ctx: MCP context for providing progress updates
        as_json: Whether to return the output as JSON
        
    Returns:
        str: A string containing either:
            - A formatted list of environments (default)
            - A JSON string with environment details (if as_json=True)
            
    Examples:
        "List all conda environments"
        "Show available environments as JSON"
    """
    status = await async_conda.env("list", as_json=as_json)
    await wait_for_command(status.pid)
    if as_json:
        return async_conda.get_json_response(status.pid)
    else:
        return async_conda.get_process_log(status.pid)

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
    """Create a new conda environment.

    This tool executes the conda create command to create a new conda environment with specified packages and configuration asynchronously. The environment can be created from a list of packages, an environment file, or by cloning an existing environment.

    After the command is executed, the function returns a ProcessStatus object for tracking the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus for tracking the command's execution, use get_command_status 
        to get the status of a running command.

    Examples:
        "Create a new environment named 'myenv' with python and numpy"
        "Create environment from environment.yml file"
        "Clone existing environment 'base' to 'newenv'"
        "Create environment with specific python version"
    """
        
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
        dev=dev
        )
        
    return status

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

    This tool executes the conda remove command to remove packages from the specified (or current) conda environment asynchronously. It can also remove all packages or the entire environment if requested. After the command is executed, the function returns a ProcessStatus object for tracking the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus for tracking the command's execution, use get_command_status 
        to get the status of a running command.


    Examples:
        "Remove package from current environment"
        "Remove packages from specific environment"
        "Remove all packages and the environment"
        "Remove all packages but keep the environment"
    """

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
        dev=dev
        )
        
    return status

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
    
    status = await async_conda.help(command)
    await wait_for_command(status.pid)
    response = async_conda.get_process_log(status.pid)
    return response


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

    This tool executes the conda list command to display all packages installed in the specified (or current) conda environment asynchronously. It supports various output formats and filtering options. After the command is executed, the function returns a ProcessStatus object for tracking the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus for tracking the command's execution, use get_command_status 
        to get the status of a running command.


    Examples:
        "List all packages in current environment"
        "Show packages in environment myenv"
        "List python packages in current environment"
        "Export package list for environment myenv"
        "Show installed packages with their channels"
        "List with explicit URLs and SHA256 hashes"
    """
  
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
        )
        
    return status

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

    This tool executes the conda clean command to remove unused conda packages and caches to free up disk space asynchronously. It can clean various types of conda caches and temporary files. After the command is executed, the function returns a ProcessStatus object for tracking the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus for tracking the command's execution, use get_command_status 
        to get the status of a running command.


    Examples:
        "Clean all caches"
        "Remove only tarballs"
        "Clean index cache and packages"
    """

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
        )
    return status

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
    """
    This tool executes the conda compare command to compare packages in an environment against those specified in an environment file asynchronously. It helps identify differences in package versions and specifications. After the command is executed, the function returns a ProcessStatus object for tracking the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus for tracking the command's execution, use get_command_status 
        to get the status of a running command.


    Examples:
        "export environments A and B to yaml files and run conda compare"
        "Compare current environment with environment.yml"
        "Compare environment myenv with path/to/environment.yml"
        "Show detailed comparison with environment.yml"
    """

        
    # Run the conda compare command
    status = await async_conda.compare(
        file=file,
        name=name,
        prefix=prefix,
        verbose=verbose,
        quiet=quiet,
        as_json=as_json,
        console=console,
        )
    
    return status


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
    """This tool provides detailed information about the conda installation and environments.

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
        )
    
    # Since info is short-running, we can wait for the process to finish
    await wait_for_command(status.pid)
    if as_json:
        return async_conda.get_json_response(status.pid)
    else:
        return async_conda.get_process_log(status.pid)

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
    """ This tool executes the conda search command to search for packages in conda channels.
        After the command is executed, the function returns a ProcessStatus object for tracking 
        the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus for tracking the command's execution, use get_command_status 
        to get the status of a running command.

    Examples:
        "Search for scipy in conda-forge channel"
    """
        
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
        use_index_cache=use_index_cache
        )

    return status

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
    """This tool allows running commands or executables within a specific conda environment asynchronously. It provides options for specifying the environment, working directory, and capturing output. After the command is executed, the function returns a ProcessStatus object for tracking the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus for tracking the command's execution, use get_command_status 
        to get the status of a running command.


    Examples:
        "Run python --version in environment myenv"
        "Execute script.py with arguments in environment py39"
        "Run jupyter notebook in data-science-env"
    """

    # Run the conda run command
    status = await async_conda.run(
        executable_call=executable_call,
        name=name,
        prefix=prefix,
        verbose=verbose,
        dev=dev,
        debug_wrapper_scripts=debug_wrapper_scripts,
        cwd=cwd,
        no_capture_output=no_capture_output
        )
        
    return status

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
    """This tool exports the specification of a conda environment, which can be used to recreate the environment on another system. After the command is executed, the function returns a ProcessStatus object for tracking the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus for tracking the command's execution, use get_command_status 
        to get the status of a running command.


    Examples:
        "Export the current environment"
        "Export to a file"
    """

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
    )   

    return status

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
    """This tool accepts a list of package specifications (e.g, bitarray=0.8) and installs a set of packages 
    consistent with those specifications and compatible with the underlying environment. After the command is executed, the function returns a ProcessStatus object for tracking the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus: Status object tracking command execution, containing the command, args, 
        process ID, output / log file, return code and other relevant information for tracking
        the command's execution.

    Examples:
        "Install scipy in current environment"
        "Install packages in specific environment"
        "Install specific version of python"
    """        
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
    )
        
    return status

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
    """This tool updates conda packages to the latest compatible version. It accepts a list of package names and updates them to the latest versions that are compatible with all other packages in the environment. After the command is executed, the function returns a ProcessStatus object for tracking the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus for tracking the command's execution, use get_command_status 
        to get the status of a running command.


    Examples:
        "Update scipy in current environment"
        "Update all packages in environment myenv"
        "Update packages from requirements.txt"
        "Update with specific channel priority"
    """
   
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
        file=file
    )
    
    return status

@mcp.tool()
async def env(
    ctx: Context,
    command: str,
    name: Optional[str] = None,
    prefix: Optional[str] = None,
    packages: Optional[List[str]] = None,
    channels: Optional[List[str]] = None,
    override_channels: bool = False,
    use_local: bool = False,
    as_json: bool = True,
    quiet: bool = False,
    verbose: bool = False,
    offline: bool = False,
) -> Dict[str, Any]:
    """This tool executes the conda environment commands like list, create, remove, export, update, and config. 
    After the command is executed, the function returns a ProcessStatus object for tracking the command's execution. Use get_command_status to get the status of a running command.

    Returns:
        ProcessStatus for tracking the command's execution, use get_command_status 
        to get the status of a running command.
    """

    status = await async_conda.env(
        command=command,
        name=name,
        prefix=prefix,
        packages=packages,
        channels=channels,
        override_channels=override_channels,
        use_local=use_local,
        as_json=as_json,
        quiet=quiet,
        verbose=verbose,
        offline=offline
    )
    
    return status

def run_conda_server():
    """Entry point for the conda environment MCP server"""
    mcp.run()
