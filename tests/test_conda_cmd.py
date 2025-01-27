import pytest
import pytest_asyncio
from condamcp.condacmd import AsyncCondaCmd
from condamcp.async_cmd import ProcessStatus
from typing import List, Optional
import json
import os
import asyncio

async def _wait_for_pid(runner, pid, timeout_seconds=60):
    """ Shared function for tests to use to wait for a given process to finish 
    
    Args:
        runner: The AsyncCondaCmd instance
        pid: Process ID to wait for
        timeout_seconds: Maximum time to wait in seconds (default: 60)
    """
    iterations = int(timeout_seconds * 10)  # Convert seconds to iterations (0.1s sleep per iteration)
    for _ in range(iterations):
        proc_status = runner.get_process(pid)
        if proc_status['status'] in ['completed', 'failed']:
            break
        await asyncio.sleep(0.1)
    else:
        raise TimeoutError(f"Process {pid} did not complete within {timeout_seconds} seconds")

@pytest_asyncio.fixture
async def conda(tmp_path):
    """Fixture providing an AsyncCondaCmd instance for testing.
    
    Args:
        tmp_path: Pytest fixture providing a temporary directory unique to each test function.
    """
    # Create logs directory in the temporary path
    logs_dir = tmp_path / "conda_logs"
    logs_dir.mkdir(exist_ok=True)
    
    cmd = AsyncCondaCmd(track_processes=True, log_dir=str(logs_dir))
    yield cmd
    # Clean up any tracked processes and background tasks
    await cmd.teardown()

@pytest.mark.asyncio
async def test_conda_env_list(conda):
    """Test conda env list command."""
    status = await conda.env("list", as_json=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid)    
    # Parse the JSON output from the log
    json_output = conda.get_json_response(status.pid)
    assert isinstance(json_output, dict)

@pytest.mark.asyncio
async def test_conda_env_export(conda):
    """Test conda env export command."""
    status = await conda.env("export", as_json=True)  # Use JSON output for more reliable parsing
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid)
    
    # Parse the JSON output from the log
    json_output = conda.get_json_response(status.pid)
    assert isinstance(json_output, dict)
    assert "dependencies" in json_output  # Check for dependencies key in JSON output

@pytest.mark.asyncio
async def test_conda_remove(conda):
    """Test conda remove command."""
    # Test removing a non-existent package (should fail gracefully)
    status = await conda.remove(packages=["nonexistentpackage123"], yes=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid)
    assert status.return_code != 0  # Should fail because package doesn't exist

@pytest.mark.asyncio
async def test_conda_create_and_remove_env(conda, tmp_path):
    """Test conda create and remove environment commands."""
    test_env = f"test_env_{tmp_path.name}"  # Use unique name based on temp directory
    
    # Create environment
    create_status = await conda.create(name=test_env, packages=["python=3.12"], yes=True)
    assert isinstance(create_status, ProcessStatus)
    await _wait_for_pid(conda, create_status.pid, timeout_seconds=120)
    assert create_status.return_code == 0
    
    # Remove environment
    remove_status = await conda.remove(name=test_env, all=True, yes=True)
    assert isinstance(remove_status, ProcessStatus)
    await _wait_for_pid(conda, remove_status.pid, timeout_seconds=120)
    assert remove_status.return_code == 0

@pytest.mark.asyncio
async def test_conda_install(conda):
    """Test conda install command."""
    # Test installing a specific package
    status = await conda.install(packages=["pip"], yes=True)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0

@pytest.mark.asyncio
async def test_conda_list(conda):
    """Test conda list command."""
    # Test JSON output
    status = await conda.list(as_json=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    json_output = conda.get_json_response(status.pid)
    assert isinstance(json_output, list)  # Conda list returns a list of package dictionaries
    assert len(json_output) > 0  # Should have at least one package
    assert isinstance(json_output[0], dict)  # Each item should be a package dict

@pytest.mark.asyncio
async def test_conda_clean(conda):
    """Test conda clean command."""
    # Test cleaning index cache
    status = await conda.clean(index_cache=True, yes=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0

@pytest.mark.asyncio
async def test_conda_run(conda):
    """Test conda run command."""
    # Test running a simple Python command that prints to stdout
    
    status = await conda.run(
        ["python", "--version"],
    )
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    # Check both stdout and stderr since output could be in either
    assert "Python" in output, "Python version not found in output"

@pytest.mark.asyncio
async def test_conda_help(conda):
    """Test conda help command."""
    status = await conda.help("env")
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    print(f"Output lines: {output}")
    assert len(output) > 0
 
    # Check for expected keywords in the help output
    assert "usage:" in output and "conda env" in output
    assert "command" in output
    assert any(cmd in output for cmd in ["create", "list", "remove", "export"])

@pytest.mark.asyncio
async def test_json_output_parsing(conda):
    """Test JSON output parsing functionality."""
    # Test with env list
    status = await conda.env("list", as_json=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    # Parse the JSON output from the log
    json_output = conda.get_json_response(status.pid)
    assert isinstance(json_output, dict)
    assert "envs" in json_output

@pytest.mark.asyncio
async def test_error_handling(conda):
    """Test error handling in conda commands."""
    # Test with invalid environment name
    status = await conda.remove(name="nonexistent_env_xyz", all=True, yes=True)
    assert isinstance(status, ProcessStatus)
    assert status.return_code != 0
    assert status.stderr is not None

@pytest.mark.asyncio
async def test_conda_upgrade(conda, tmp_path):
    """Test conda upgrade command."""
    # Test upgrading a specific package in a test environment
    test_env = f"test_env_{tmp_path.name}"  # Use unique name based on temp directory
    try:
        status =await conda.create(name=test_env, packages=["python=3.12"], yes=True)
        await _wait_for_pid(conda, status.pid, timeout_seconds=120)
        assert status.return_code == 0
        # install pip in the test environment
        status = await conda.install(name=test_env, packages=["pip"], yes=True)
        assert isinstance(status, ProcessStatus)
        await _wait_for_pid(conda, status.pid, timeout_seconds=120)
        output = conda.get_process_log(status.pid)
        assert status.return_code == 0

        # upgrade pip in the test environment
        status = await conda.upgrade(name=test_env, packages=["pip"], yes=True)
        assert isinstance(status, ProcessStatus)
        await _wait_for_pid(conda, status.pid, timeout_seconds=120)
        assert status.return_code == 0
    finally:
        # Always remove the test environment, even if test fails
        status = await conda.remove(name=test_env, all=True, yes=True)
        assert isinstance(status, ProcessStatus)
        await _wait_for_pid(conda, status.pid, timeout_seconds=120)

@pytest.mark.asyncio
async def test_environment_variables(conda):
    """Test that conda commands respect environment variables."""
    # Verify conda binary path is set
    assert conda.binary_path is not None
    assert len(conda.binary_path) > 0

@pytest.mark.asyncio
async def test_conda_compare(conda, tmp_path):
    """Test conda compare command with two test environments."""
    # Create two test environments with different packages
    env1_name = f"test_env_1_{tmp_path.name}"  # Use unique names based on temp directory
    env2_name = f"test_env_2_{tmp_path.name}"
    env_file = "test_env_1.yml"  # Define env_file at the top level
    
    try:
        # Create first environment with numpy
        status = await conda.create(name=env1_name, packages=["python=3.9", "numpy"], yes=True)
        assert isinstance(status, ProcessStatus)
        await _wait_for_pid(conda, status.pid, timeout_seconds=120)
        assert status.return_code == 0
        
        # Create second environment with pandas (which includes numpy as dependency)
        status = await conda.create(name=env2_name, packages=["python=3.9", "pandas"], yes=True)
        assert isinstance(status, ProcessStatus)
        await _wait_for_pid(conda, status.pid, timeout_seconds=120)
        assert status.return_code == 0
        
        # Export first environment to file
        status = await conda.env("export", name=env1_name, as_json=True)
        assert isinstance(status, ProcessStatus)
        await _wait_for_pid(conda, status.pid, timeout_seconds=120)
        assert status.return_code == 0
        
        # Parse the JSON output from the log
        json_output = conda.get_json_response(status.pid)
        assert isinstance(json_output, dict)
        # Write environment file
        with open(env_file, "w") as f:
            json.dump(json_output, f)
        
        # Compare second environment with first environment's file
        status = await conda.compare(
            file=env_file,
            name=env2_name,
            as_json=True,
        )
        assert isinstance(status, ProcessStatus)
        await _wait_for_pid(conda, status.pid, timeout_seconds=120)
        
        # Expect return code 1 since environments should be different
        assert status.return_code == 1, "Expected differences between environments"
        
        # Get the comparison output from the log and parse it
        differences = conda.get_json_response(status.pid)
        assert isinstance(differences, list), "Expected JSON array of differences"
        assert len(differences) > 0, "Expected at least one difference"
        
        # Check for expected differences - either numpy directly or as a dependency
        assert any("numpy" in diff for diff in differences), "Expected numpy version difference not found"
        assert any("mismatch" in diff for diff in differences), "Expected package mismatch indicator not found"
        
    finally:
        # Clean up environments and file
        status = await conda.remove(name=env1_name, all=True, yes=True)
        assert isinstance(status, ProcessStatus)
        await _wait_for_pid(conda, status.pid, timeout_seconds=120)
        status = await conda.remove(name=env2_name, all=True, yes=True)
        assert isinstance(status, ProcessStatus)
        await _wait_for_pid(conda, status.pid, timeout_seconds=120)
        if os.path.exists(env_file):
            os.remove(env_file)

@pytest.mark.asyncio
async def test_conda_search(conda):
    """Test conda search command."""
    # Test basic package search
    status = await conda.search("scikit-learn")
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    assert "scikit-learn" in output.lower()

    # Test wildcard search
    status = await conda.search("*scikit*")
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    assert "scikit" in output.lower()

    # Test MatchSpec format with subdir
    status = await conda.search("numpy[subdir=linux-64]")
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    assert "numpy" in output.lower()

    # Test version constraint search
    status = await conda.search("numpy>=1.12")
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    assert "numpy" in output.lower()

    # Test channel-specific search
    status = await conda.search("conda-forge::numpy")
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    assert "numpy" in output.lower()

    # Test search with no results
    status = await conda.search(
        "nonexistentpackagename123456789",
        skip_flexible_search=True,  # Disable flexible matching for faster response
    )
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    # When no packages are found, conda returns code 1
    assert status.return_code == 1
    output = conda.get_process_log(status.pid)
    # Check for expected "no match" message
    assert any(
        msg in output.lower()
        for msg in ["no match", "not available", "packagenotfounderror"]
    )

    # Test search in all environments
    status = await conda.search("python", envs=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    assert "python" in output.lower()

@pytest.mark.asyncio
async def test_conda_info(conda):
    """Test conda info command with various flags."""
    # Test basic info
    status = await conda.info()
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    # Check for common info sections
    assert any(keyword in output for keyword in ["platform", "conda version", "base environment"])

    # Test JSON output with all info
    status = await conda.info(all=True, as_json=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    json_output = conda.get_json_response(status.pid)
    assert isinstance(json_output, dict)
    # Check for required keys in JSON output
    assert "conda_version" in json_output
    assert "conda_location" in json_output
    assert "channels" in json_output

    # Test environment listing
    status = await conda.info(envs=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    # Should show conda environments header and base environment
    assert "conda environments:" in output.lower()
    assert "base" in output  # Base environment is listed simply as "base"

    # Test system info
    status = await conda.info(system=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    # Should show environment variables
    assert any(var in output for var in ["PATH", "CONDA_PREFIX", "PYTHONPATH"])

    # Test unsafe channels
    status = await conda.info(unsafe_channels=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    # No assertion on content since there might not be any unsafe channels

    # Test base environment path
    status = await conda.info(base=True)
    assert isinstance(status, ProcessStatus)
    await _wait_for_pid(conda, status.pid, timeout_seconds=120)
    assert status.return_code == 0
    output = conda.get_process_log(status.pid)
    # Should show conda/miniconda base path
    assert any(path in output.lower() for path in ["conda", "miniconda"])
