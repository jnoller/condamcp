"""Server implementation for conda build commands."""

from mcp.server.fastmcp import FastMCP, Context
from pathlib import Path
from .condabuild import AsyncCondaBuild
from .async_cmd import ProcessStatus
from typing import Optional, List, Dict

mcp = FastMCP("CondaBuild")

# Set up build logs directory
logs_dir = Path.home() / ".condamcp" / "mcp" / "build_logs"
logs_dir.mkdir(parents=True, exist_ok=True)

# Initialize conda build wrapper
conda_build = AsyncCondaBuild(log_dir=str(logs_dir))

@mcp.tool()
async def build(
    ctx: Context,
    build_env: str,
    recipe_path: str,
    config_file: Optional[str] = None,
    croot: Optional[str] = None,
    channels: Optional[List[str]] = None,
    variant_config_files: Optional[List[str]] = None,
    exclusive_config_files: Optional[List[str]] = None,
    python_version: Optional[str] = None,
    perl: Optional[str] = None,
    numpy: Optional[str] = None,
    r_base: Optional[str] = None,
    lua: Optional[str] = None,
    bootstrap: Optional[str] = None,
    append_file: Optional[str] = None,
    clobber_file: Optional[str] = None,
    old_build_string: bool = False,
    use_channeldata: bool = False,
    variants: Optional[str] = None,
    check: bool = False,
    no_include_recipe: bool = False,
    source: bool = False,
    test: bool = False,
    no_test: bool = False,
    build_only: bool = False,
    post: bool = False,
    test_run_post: bool = False,
    skip_existing: bool = False,
    keep_old_work: bool = False,
    dirty: bool = False,
    debug: bool = False,
    token: Optional[str] = None,
    user: Optional[str] = None,
    label: Optional[str] = None,
    no_force_upload: bool = False,
    zstd_compression_level: Optional[int] = None,
    password: Optional[str] = None,
    sign: Optional[str] = None,
    sign_with: Optional[str] = None,
    identity: Optional[str] = None,
    repository: Optional[str] = None,
    no_activate: bool = False,
    no_build_id: bool = False,
    build_id_pat: Optional[str] = None,
    verify: bool = False,
    no_verify: bool = False,
    strict_verify: bool = False,
    output_folder: Optional[str] = None,
    no_prefix_length_fallback: bool = False,
    prefix_length_fallback: bool = False,
    prefix_length: Optional[int] = None,
    no_locking: bool = False,
    no_remove_work_dir: bool = False,
    error_overlinking: bool = False,
    no_error_overlinking: bool = False,
    error_overdepending: bool = False,
    no_error_overdepending: bool = False,
    long_test_prefix: bool = False,
    no_long_test_prefix: bool = False,
    keep_going: bool = False,
    cache_dir: Optional[str] = None,
    no_copy_test_source_files: bool = False,
    merge_build_host: bool = False,
    stats_file: Optional[str] = None,
    extra_deps: Optional[List[str]] = None,
    extra_meta: Optional[Dict[str, str]] = None,
    suppress_variables: bool = False,
    use_local: bool = False,
    override_channels: bool = False,
    repodata_fn: Optional[List[str]] = None,
    experimental: Optional[str] = None,
    no_lock: bool = False,
    repodata_use_zst: Optional[bool] = None,
    env: Optional[Dict[str, str]] = None,
    quiet: bool = False
) -> ProcessStatus:
    """Build a conda package from a recipe.
    
    This tool starts a conda build process and returns a process ID that can be used
    to check the status and logs using get_build_status() and get_build_log().
        
    Returns:
        ProcessStatus: Process status object
        
    Examples:
        "Build the package in /path/to/recipe"
        "Build the recipe using config file /path/to/config.yaml"
        "Build the package and use the conda-forge channel"
    """
    try:
        ctx.info(f"Starting conda build for recipe at '{recipe_path}'...")
        await ctx.report_progress(0, 2)
        
        # Run the conda build command
        status = await conda_build.build(
            build_env=build_env,
            recipe_path=recipe_path,
            config_file=config_file,
            croot=croot,
            channels=channels,
            variant_config_files=variant_config_files,
            exclusive_config_files=exclusive_config_files,
            python_version=python_version,
            perl=perl,
            numpy=numpy,
            r_base=r_base,
            lua=lua,
            bootstrap=bootstrap,
            append_file=append_file,
            clobber_file=clobber_file,
            old_build_string=old_build_string,
            use_channeldata=use_channeldata,
            variants=variants,
            check=check,
            no_include_recipe=no_include_recipe,
            source=source,
            test=test,
            no_test=no_test,
            build_only=build_only,
            post=post,
            test_run_post=test_run_post,
            skip_existing=skip_existing,
            keep_old_work=keep_old_work,
            dirty=dirty,
            debug=debug,
            token=token,
            user=user,
            label=label,
            no_force_upload=no_force_upload,
            zstd_compression_level=zstd_compression_level,
            password=password,
            sign=sign,
            sign_with=sign_with,
            identity=identity,
            repository=repository,
            no_activate=no_activate,
            no_build_id=no_build_id,
            build_id_pat=build_id_pat,
            verify=verify,
            no_verify=no_verify,
            strict_verify=strict_verify,
            output_folder=output_folder,
            no_prefix_length_fallback=no_prefix_length_fallback,
            prefix_length_fallback=prefix_length_fallback,
            prefix_length=prefix_length,
            no_locking=no_locking,
            no_remove_work_dir=no_remove_work_dir,
            error_overlinking=error_overlinking,
            no_error_overlinking=no_error_overlinking,
            error_overdepending=error_overdepending,
            no_error_overdepending=no_error_overdepending,
            long_test_prefix=long_test_prefix,
            no_long_test_prefix=no_long_test_prefix,
            keep_going=keep_going,
            cache_dir=cache_dir,
            no_copy_test_source_files=no_copy_test_source_files,
            merge_build_host=merge_build_host,
            stats_file=stats_file,
            extra_deps=extra_deps,
            extra_meta=extra_meta,
            suppress_variables=suppress_variables,
            use_local=use_local,
            override_channels=override_channels,
            repodata_fn=repodata_fn,
            experimental=experimental,
            no_lock=no_lock,
            repodata_use_zst=repodata_use_zst,
            env=env,
            quiet=quiet
        )
        
        await ctx.report_progress(2, 2)  # Mark as complete
        
        return status
        
    except Exception as e:
        ctx.error(f"Error: {str(e)}")
        raise  # Re-raise the exception to properly handle it in the MCP framework

@mcp.tool()
def cancel_build(pid: int):
    """Cancel a running conda build.
    
    Args:
        pid: Process ID of the build to cancel
    """
    try:
        conda_build.kill_process(pid)
        return f"Build {pid} cancelled successfully"
    except Exception as e:
        return f"Failed to cancel build {pid}: {e}"


@mcp.tool()
async def get_build_status(pid: int) -> str:
    """Get the status of a conda build.
    Args:
        pid: The process ID returned from build_package
    Returns:
        str: Build status

    Examples:
        "What is the status of the build?"
        "Check the status of my latest build"
        "What is the status of build 1234567890?"
    """
    status = await conda_build.get_process(pid)
    if status['status'] in ['completed', 'failed']:
        return f"Build {pid} status: {status['status']}"
    else:
        return f"Build {pid} is still running"

@mcp.tool()
async def get_build_log(pid: int, tail: int | None = None) -> str:
    """Get some or all of the log output from a conda build.
    Args:
        pid: The process ID returned from build_package
        tail: Number of lines to return from end of log (None for all)
    Returns:
        str: Build log output

    Examples:
        "Show me the log for build 1234567890"
        "What is the log for my latest build?"
        "Show the last 100 lines of the log for build 1234567890"
    """
    status = await conda_build.get_process(pid)
    if status['status'] in ['completed', 'failed']:
        if status.log_file:
            return await conda_build.get_process_log(pid)
        else:
            return f"No log file available for build {pid}"
    else:
        return f"Build {pid} is still running"

@mcp.prompt()
def create_build_environment_prompt(name: str) -> str:
    """Prompt to create a conda environment for package building"""
    prompt = f"""Create a new conda environment called {name} using python3.12 and install these packages:
* conda-build
* distro-tooling::anaconda-linter
* anaconda-client
* conda-package-handling
Remember that installing all of these packages at once will take a while so it is 
better to install them one by one and inform the user when each step is complete.
Use quiet and other options to make the installation process as terse as possible.
"""
    return prompt

@mcp.prompt()
def build_llamacpp_prompt(name: str):
    prompt = f"""Using the {name} environment, build the llama.cpp package for me:

*	Recipe path: /Users/jesse/Code/conda-feedstocks/llama.cpp-feedstock
*	Conda build config: /Users/jesse/Code/conda-feedstocks/conda_build_config.yaml
*	Build root: /Users/jesse/Code/conda-feedstocks/builds
*	Additional channel for the build: ai-staging

This package generates 3 different packages:

*	gguf
*	llama.cpp-tools
*	llama.cpp

Remember: 
* If the build fails, please show me the logs and suggest a possible solution.
* Please continue to monitor the build output until all packages are built.
* If the build succeeds, please tell me what directory to open to access the files.
"""
    return prompt

def run_build_server():
    """Run the conda build server."""
    mcp.run()
