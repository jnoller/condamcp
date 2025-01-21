import pytest
import pytest_asyncio
from condamcp.condacmd import AsyncCondaCmd
from condamcp.async_cmd import ProcessStatus
from typing import List, Optional
import json

@pytest_asyncio.fixture
async def conda():
    """Fixture providing an AsyncCondaCmd instance for testing."""
    cmd = AsyncCondaCmd()
    yield cmd

@pytest.mark.asyncio
async def test_conda_env_list(conda):
    """Test conda env list command."""
    status = await conda.env("list", as_json=True)
    assert isinstance(status, tuple)
    assert len(status) == 2
    assert isinstance(status[0], ProcessStatus)
    assert isinstance(status[1], dict)

@pytest.mark.asyncio
async def test_conda_env_export(conda):
    """Test conda env export command."""
    status = await conda.env("export", as_json=True)  # Use JSON output for more reliable parsing
    assert isinstance(status, tuple)
    assert len(status) == 2
    assert isinstance(status[1], dict)
    assert "dependencies" in status[1]  # Check for dependencies key in JSON output

@pytest.mark.asyncio
async def test_conda_remove(conda):
    """Test conda remove command."""
    # Test removing a non-existent package (should fail gracefully)
    status = await conda.remove(packages=["nonexistentpackage123"], yes=True)
    assert isinstance(status, ProcessStatus)
    assert status.return_code != 0  # Should fail because package doesn't exist

@pytest.mark.asyncio
async def test_conda_create_and_remove_env(conda):
    """Test conda create and remove environment commands."""
    test_env = "test_env_xyz"
    
    # Create environment
    create_status = await conda.create(name=test_env, packages=["python=3.9"], yes=True)
    assert isinstance(create_status, ProcessStatus)
    assert create_status.return_code == 0
    
    # Remove environment
    remove_status = await conda.remove(name=test_env, all=True, yes=True)
    assert isinstance(remove_status, ProcessStatus)
    assert remove_status.return_code == 0

@pytest.mark.asyncio
async def test_conda_install(conda):
    """Test conda install command."""
    # Test installing a specific package
    status = await conda.install(packages=["pip"], yes=True)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0

@pytest.mark.asyncio
async def test_conda_list(conda):
    """Test conda list command."""
    # Test basic list
    status = await conda.list()
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    assert status.stdout is not None

    # Test JSON output
    status = await conda.list(as_json=True)
    assert isinstance(status, tuple)
    assert len(status) == 2
    assert isinstance(status[0], ProcessStatus)
    assert isinstance(status[1], list)  # Conda list returns a list of package dictionaries
    assert len(status[1]) > 0  # Should have at least one package
    assert isinstance(status[1][0], dict)  # Each item should be a package dict

@pytest.mark.asyncio
async def test_conda_clean(conda):
    """Test conda clean command."""
    # Test cleaning index cache
    status = await conda.clean(index_cache=True, yes=True)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0

@pytest.mark.asyncio
async def test_conda_run(conda):
    """Test conda run command."""
    # Test running a simple Python command that prints to stdout
    output_lines = []
    error_lines = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output_lines.append(status.stdout)
        if status.stderr:
            error_lines.append(status.stderr)
    
    status = await conda.run(
        ["python", "--version"],
        status_callback=callback
    )
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    # Check both stdout and stderr since output could be in either
    combined_output = '\n'.join(output_lines + error_lines)
    assert "Python" in combined_output, "Python version not found in output"

@pytest.mark.asyncio
async def test_conda_help(conda):
    """Test conda help command."""
    # Get help text for conda env command
    output_lines = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output_lines.append(status.stdout)
    
    status = await conda.help("env", status_callback=callback)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    assert len(output_lines) > 0
    assert any(keyword in '\n'.join(output_lines) for keyword in ["usage:", "conda", "env"])

@pytest.mark.asyncio
async def test_json_output_parsing(conda):
    """Test JSON output parsing functionality."""
    # Test with env list
    status = await conda.env("list", as_json=True)
    assert isinstance(status, tuple)
    assert len(status) == 2
    assert isinstance(status[1], dict)
    assert "envs" in status[1]

@pytest.mark.asyncio
async def test_error_handling(conda):
    """Test error handling in conda commands."""
    # Test with invalid environment name
    status = await conda.remove(name="nonexistent_env_xyz", all=True, yes=True)
    assert isinstance(status, ProcessStatus)
    assert status.return_code != 0
    assert status.stderr is not None

@pytest.mark.asyncio
async def test_callback_functionality(conda):
    """Test callback functionality."""
    output_lines = []
    
    def callback(status: ProcessStatus):
        if status.stdout:
            output_lines.append(status.stdout)
    
    status = await conda.list(status_callback=callback)
    assert len(output_lines) > 0
    assert all(isinstance(line, str) for line in output_lines)

@pytest.mark.asyncio
async def test_conda_upgrade(conda):
    """Test conda upgrade command."""
    # Test upgrading a specific package in a test environment
    test_env = "test_env_xyz"
    await conda.create(name=test_env, packages=["python=3.9"], yes=True)
    # install pip in the test environment
    status = await conda.install(name=test_env, packages=["pip"], yes=True)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    # upgrade pip in the test environment
    status = await conda.upgrade(name=test_env, packages=["pip"], yes=True)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    # remove the test environment
    status = await conda.remove(name=test_env, all=True, yes=True)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0

@pytest.mark.asyncio
async def test_environment_variables(conda):
    """Test that conda commands respect environment variables."""
    # Verify conda binary path is set
    assert conda.binary_path is not None
    assert len(conda.binary_path) > 0

@pytest.mark.asyncio
async def test_conda_compare(conda):
    """Test conda compare command with two test environments."""
    # Create two test environments with different packages
    env1_name = "test_env_1"
    env2_name = "test_env_2"
    
    try:
        # Create first environment with numpy
        create_status = await conda.create(name=env1_name, packages=["python=3.9", "numpy"], yes=True)
        assert create_status.return_code == 0
        
        # Create second environment with pandas (which includes numpy as dependency)
        create_status = await conda.create(name=env2_name, packages=["python=3.9", "pandas"], yes=True)
        assert create_status.return_code == 0
        
        # Export first environment to file
        status = await conda.env("export", "-n", env1_name, as_json=True)
        assert isinstance(status, tuple)
        assert status[0].return_code == 0
        
        # Write environment file
        env_file = "test_env_1.yml"
        with open(env_file, "w") as f:
            json.dump(status[1], f)
        
        # Compare second environment with first environment's file
        compare_lines = []
        error_lines = []
        def compare_callback(status: ProcessStatus):
            if status.stdout:
                compare_lines.append(status.stdout)
            if status.stderr:
                error_lines.append(status.stderr)
        
        status = await conda.compare(
            file=env_file,
            name=env2_name,
            as_json=True,
            status_callback=compare_callback
        )
        
        # Expect return code 1 since environments should be different
        assert status.return_code == 1, "Expected differences between environments"
        
        # Parse and verify the JSON output
        comparison_output = "".join(compare_lines)
        try:
            differences = json.loads(comparison_output)
            assert isinstance(differences, list), "Expected JSON array of differences"
            assert len(differences) > 0, "Expected at least one difference"
            
            # Convert differences to string for easier searching
            diff_str = json.dumps(differences)
            # Check for expected differences
            assert "numpy" in diff_str, "Expected numpy version difference not found"
            assert "mismatch" in diff_str, "Expected package mismatch indicator not found"
            
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse JSON output: {e}\nOutput was: {comparison_output}")
        
    finally:
        # Clean up environments and file
        await conda.remove(name=env1_name, all=True, yes=True)
        await conda.remove(name=env2_name, all=True, yes=True)
        import os
        if os.path.exists(env_file):
            os.remove(env_file)

@pytest.mark.asyncio
async def test_conda_search(conda):
    """Test conda search command."""
    output_lines = []
    error_lines = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output_lines.append(status.stdout)
        if status.stderr:
            error_lines.append(status.stderr)

    def print_debug_info(test_name: str, status: ProcessStatus):
        print(f"\nDebugging {test_name}:")
        print(f"Command: {status.cmd}")
        print(f"Args: {status.args}")
        print(f"Return code: {status.return_code}")
        print(f"Stdout: '{status.stdout}'")
        print(f"Stderr: '{status.stderr}'")
        print(f"Error: {status.error}")
        print(f"Accumulated stdout: {output_lines}")
        print(f"Accumulated stderr: {error_lines}")

    # Test basic package search
    status = await conda.search("scikit-learn", status_callback=callback)
    print_debug_info("basic package search", status)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    assert "scikit-learn" in combined_output.lower()

    # Test wildcard search
    output_lines.clear()
    error_lines.clear()
    status = await conda.search("*scikit*", status_callback=callback)
    print_debug_info("wildcard search", status)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    assert "scikit" in combined_output.lower()

    # Test MatchSpec format with subdir
    output_lines.clear()
    error_lines.clear()
    status = await conda.search(
        "numpy[subdir=linux-64]",
        status_callback=callback
    )
    print_debug_info("MatchSpec search", status)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    assert "numpy" in combined_output.lower()

    # Test version constraint search
    output_lines.clear()
    error_lines.clear()
    status = await conda.search(
        "numpy>=1.12",
        status_callback=callback
    )
    print_debug_info("version constraint search", status)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    assert "numpy" in combined_output.lower()

    # Test channel-specific search
    output_lines.clear()
    error_lines.clear()
    status = await conda.search(
        "conda-forge::numpy",
        status_callback=callback
    )
    print_debug_info("channel-specific search", status)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    assert "numpy" in combined_output.lower()

    # Test search with detailed info and JSON output
    output_lines.clear()
    error_lines.clear()
    status, json_data = await conda.search(
        "python",
        info=True,
        as_json=True,
        status_callback=callback
    )
    print_debug_info("JSON search", status)
    print(f"JSON data: {json_data}")
    assert status.return_code == 0
    assert isinstance(json_data, dict)
    # Detailed info should include version, build, and channel info
    package_str = str(json_data)
    assert any(key in package_str for key in ["version", "build", "channel"])

    # Test search with repodata options
    output_lines.clear()
    error_lines.clear()
    status = await conda.search(
        "numpy",
        repodata_fn=["current_repodata.json"],
        experimental="lock",
        no_lock=False,
        repodata_use_zst=True,
        status_callback=callback
    )
    print_debug_info("repodata search", status)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    assert "numpy" in combined_output.lower()

    # Test search with network options
    output_lines.clear()
    error_lines.clear()
    print("\nTesting network options search:")
    print("Conda binary path:", conda.binary_path)
    
    # First try without offline mode to verify basic search works
    status = await conda.search(
        "python",
        use_index_cache=True,
        insecure=True,
        status_callback=callback
    )
    print_debug_info("network options (without offline)", status)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    assert "python" in combined_output.lower()
    
    # Now try with offline mode - expect failure
    output_lines.clear()
    error_lines.clear()
    status = await conda.search(
        "python",
        use_index_cache=True,
        insecure=True,
        offline=True,
        status_callback=callback
    )
    print_debug_info("network options (with offline)", status)
    # In offline mode, expect return code 1 and appropriate error message
    assert status.return_code == 1
    combined_stderr = "\n".join(error_lines)
    assert "PackagesNotFoundError" in combined_stderr
    assert "Current channels:" in combined_stderr
    assert "To search for alternate channels" in combined_stderr

    # Test search with no results
    output_lines.clear()
    error_lines.clear()
    status = await conda.search(
        "nonexistentpackagename123456789",
        skip_flexible_search=True,  # Disable flexible matching for faster response
        status_callback=callback
    )
    print_debug_info("no results search", status)
    # When no packages are found, conda returns code 1
    assert status.return_code == 1
    combined_output = "\n".join(output_lines)
    combined_stderr = "\n".join(error_lines)
    # Check for expected "no match" message in either stdout or stderr
    assert any(
        msg in combined_output.lower() or msg in combined_stderr.lower()
        for msg in ["no match", "not available", "packagenotfounderror"]
    )

    # Test search in all environments
    output_lines.clear()
    error_lines.clear()
    status = await conda.search(
        "python",
        envs=True,
        status_callback=callback
    )
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    assert "python" in combined_output.lower()

@pytest.mark.asyncio
async def test_conda_info(conda):
    """Test conda info command with various flags."""
    output_lines = []
    error_lines = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output_lines.append(status.stdout)
        if status.stderr:
            error_lines.append(status.stderr)

    # Test basic info
    status = await conda.info(status_callback=callback)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    # Check for common info sections
    assert any(keyword in combined_output for keyword in ["platform", "conda version", "base environment"])

    # Test JSON output with all info
    output_lines.clear()
    error_lines.clear()
    status, json_data = await conda.info(all=True, as_json=True, status_callback=callback)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    assert isinstance(json_data, dict)
    # Check for required keys in JSON output
    assert "conda_version" in json_data
    assert "conda_location" in json_data
    assert "channels" in json_data

    # Test environment listing
    output_lines.clear()
    error_lines.clear()
    status = await conda.info(envs=True, status_callback=callback)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    # Should show conda environments header and base environment
    assert "conda environments:" in combined_output.lower()
    assert "base" in combined_output  # Base environment is listed simply as "base"

    # Test system info
    output_lines.clear()
    error_lines.clear()
    status = await conda.info(system=True, status_callback=callback)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    # Should show environment variables
    assert any(var in combined_output for var in ["PATH", "CONDA_PREFIX", "PYTHONPATH"])

    # Test unsafe channels
    output_lines.clear()
    error_lines.clear()
    status = await conda.info(unsafe_channels=True, status_callback=callback)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    # No assertion on content since there might not be any unsafe channels

    # Test base environment path
    output_lines.clear()
    error_lines.clear()
    status = await conda.info(base=True, status_callback=callback)
    assert isinstance(status, ProcessStatus)
    assert status.return_code == 0
    combined_output = "\n".join(output_lines)
    # Should show conda/miniconda base path
    assert any(path in combined_output.lower() for path in ["conda", "miniconda"])
