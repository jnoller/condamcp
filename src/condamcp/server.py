from condamcp.condacmd import Condacmd
from condamcp.condabuild import CondaBuild
from mcp.server.fastmcp import FastMCP
from pathlib import Path
import tempfile

mcp = FastMCP("Conda")
conda = Condacmd(use_shell=True)

# Create logs directory in user's home or temp
logs_dir = Path.home() / ".conda-mcp" / "logs"
# or
logs_dir = Path(tempfile.gettempdir()) / "conda-mcp-logs"

logs_dir.mkdir(parents=True, exist_ok=True)
conda_build = CondaBuild(use_shell=True, build_env="build", logs_dir=str(logs_dir))

@mcp.tool()
def environment_list(
    as_json: bool = False,
    verbose: bool = False,
    quiet: bool = False
) -> str:
    """List all conda environments in the system.

    This tool displays all conda environments that are currently installed,
    including their names and paths.

    Args:
        as_json: Return the environment list in JSON format instead of text
        verbose: Show additional details about environments
        quiet: Minimize output (suppress progress bars)

    Returns:
        A string containing either:
        - A formatted list of conda environments (default)
        - A JSON string with environment details (if as_json=True)

    Examples:
        "List all my conda environments"
        "Show me my conda environments in JSON format" (sets as_json=True)
        "List conda environments with detailed information" (sets verbose=True)
    """
    result = conda.env_list(
        as_json=as_json,
        verbose=verbose,
        quiet=quiet
    )
    
    if as_json and isinstance(result, dict):
        import json
        return json.dumps(result, indent=2)
    return result


@mcp.tool()
def environment_create(
    name: str,
    packages: list[str] = None,
    file: str = None,
    quiet: bool = False,
    dry_run: bool = False,
    as_json: bool = False
) -> str:
    """Create a new conda environment.

    This tool creates a new conda environment with the specified name and packages.
    You can either specify packages directly or use an environment.yml file.

    Args:
        name: Name of the environment to create
        packages: List of packages to install in the environment
        file: Path to environment.yml file to use for creation
        quiet: Minimize output (suppress progress bars)
        dry_run: Show what would be done without actually creating
        as_json: Return the output in JSON format

    Returns:
        A string containing the creation output or error message

    Examples:
        "Create a new environment named 'myenv' with python and numpy"
        "Create environment 'testenv' from environment.yml"
        "Create a python environment named 'dev' and show what packages would be installed"
    """
    returncode, stdout, stderr = conda.env_create(
        name=name,
        packages=packages,
        file=file,
        quiet=quiet,
        dry_run=dry_run,
        as_json=as_json
    )
    
    if stderr:
        return f"Error creating environment: {stderr}"
    return stdout


@mcp.tool()
def environment_remove(
    name: str,
    dry_run: bool = False,
    quiet: bool = False,
    as_json: bool = False,
    yes: bool = True
) -> str:
    """Remove a conda environment.

    This tool removes the specified conda environment. The environment
    must be deactivated before it can be removed.

    Args:
        name: Name of the environment to remove
        dry_run: Show what would be done without actually removing
        quiet: Minimize output (suppress progress bars)
        as_json: Return the output in JSON format
        yes: Don't ask for confirmation (defaults to True)

    Returns:
        A string containing the removal output or error message

    Examples:
        "Remove the environment named 'myenv'"
        "Delete environment 'testenv' and show what would be removed"
        "Remove environment 'dev' without any prompts"
    """
    returncode, stdout, stderr = conda.env_remove(
        name=name,
        dry_run=dry_run,
        quiet=quiet,
        as_json=as_json,
        yes=yes
    )
    
    if stderr:
        return f"Error removing environment: {stderr}"
    return stdout


@mcp.tool()
def build_package(
    build_env: str,
    recipe_path: str,
    config_file: str | None = None,
    croot: str | None = None,
    channels: str | list[str] | None = None,
    variant_config_files: list[str] | None = None,
    python_version: str | None = None,
    numpy_version: str | None = None,
    output_folder: str | None = None,
    env: dict[str, str] | None = None
) -> str:
    """Start building a conda package.

    This tool starts an asynchronous conda build process and returns
    a build ID that can be used to check status and logs.

    Args:
        build_env: Name of conda environment to use for build
        recipe_path: Path to recipe directory
        config_file: Path to conda build config file
        croot: Build root directory for package
        channels: Channel(s) to search for dependencies (single channel or list)
        variant_config_files: List of variant config files
        python_version: Python version for build
        numpy_version: NumPy version for build
        output_folder: Directory to place output package
        env: Dictionary of environment variables to set for build

    Returns:
        str: Build ID for tracking the build process or error message

    Examples:
        "Build the package in ./recipe"
        "Build recipe using config.yaml and python 3.10"
        "Build package in ./recipe and output to ./dist"
        "Build recipe with custom build root directory"
    """
    try:
        build_id = conda_build.build(
            recipe_path=recipe_path,
            config_file=config_file,
            croot=croot,
            channels=channels,
            variant_config_files=variant_config_files,
            python_version=python_version,
            numpy_version=numpy_version,
            output_folder=output_folder,
            env=env
        )
        return f"Build started with ID: {build_id}"
    except ValueError as e:
        return f"Error starting build: {str(e)}"


@mcp.tool()
def check_build_status(build_id: str) -> str:
    """Check the status of a conda build process.

    Args:
        build_id: The build ID returned from build_package

    Returns:
        str: Current build status information
    """
    status = conda_build.get_build_status(build_id)
    return f"Build {build_id} status: {status}"


@mcp.tool()
def show_build_log(build_id: str, tail: int = 50) -> str:
    """Show the log output from a conda build process.

    Args:
        build_id: The build ID returned from build_package
        tail: Number of lines to show from end of log

    Returns:
        str: Build log output
    """
    return conda_build.get_build_log(build_id, tail)


@mcp.tool()
def show_help(command: str = None) -> str:
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
    returncode, stdout, stderr = conda.show_help(command)
    if stderr:
        return f"Error getting help: {stderr}"
    return stdout

