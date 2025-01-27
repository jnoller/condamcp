import pytest
import asyncio
from pathlib import Path
import tempfile
from condamcp.async_cmd import AsyncProcessRunner, CommandError, ProcessStatus
from condamcp.condacmd import AsyncCondaCmd
import sys
import re
import psutil

async def _wait_for_pid(runner, pid, timeout=30):
    """ Shared function for tests to use to wait for a given process to finish """
    for _ in range(timeout):
        proc_status = runner.get_process(pid)
        if proc_status['status'] in ['completed', 'failed']:
            break
        await asyncio.sleep(0.1)
    else:
        raise TimeoutError("Process did not complete in time")

@pytest.fixture
def runner():
    """Default runner that uses a temporary directory for logs"""
    return AsyncProcessRunner(track_processes=True)

@pytest.mark.asyncio
async def test_basic_command(runner):
    """Test basic blocking command execution without shell"""
    output = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
    
    status = await runner.execute("echo", ["hello"], status_callback=callback)
    assert status.return_code == 0
    assert "hello" in output[0]
    assert not status.stderr
    # Verify log file was created in temp directory
    assert status.log_file and status.log_file.exists()
    assert status.log_file.parent == runner.log_dir

@pytest.mark.asyncio
async def test_shell_command(runner):
    """Test blocking command execution with shell"""
    output = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
            
    runner_shell = AsyncProcessRunner(shell=True, track_processes=True)
    status = await runner_shell.execute("echo", ["hello"], status_callback=callback)
    assert status.return_code == 0
    assert "hello" in output[0]
    assert not status.stderr
    # Verify log file was created in temp directory
    assert status.log_file and status.log_file.exists()
    assert status.log_file.parent == runner_shell.log_dir

@pytest.mark.asyncio
async def test_shell_command_with_pipes(runner):
    """Test blocking shell command with shell features like pipes"""
    output = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
            
    runner_shell = AsyncProcessRunner(shell=True, track_processes=True)
    status = await runner_shell.execute("echo hello | grep hello", status_callback=callback)
    assert status.return_code == 0
    assert "hello" in output[0]
    assert not status.stderr
    # Verify log file was created
    assert status.log_file and status.log_file.exists()

@pytest.mark.asyncio
async def test_get_active_processes(runner):
    """Test forked process tracking"""
    # Start a command
    status = await runner.fork("sleep 1" if sys.platform != "win32" else "timeout 1", shell=True)
    
    # Check active processes
    active = runner.get_active_processes()
    assert len(active) == 1
    assert status.pid in active
    
    # Wait for completion by polling
    await _wait_for_pid(runner, status.pid)
    
    # Process should still be tracked after completion
    active = runner.get_active_processes()
    assert len(active) == 1
    assert status.pid in active

@pytest.mark.asyncio
async def test_get_process_status(runner):
    """Test process status tracking"""
    # Start a command
    status = await runner.fork("echo test", shell=True)

    # Wait for completion by polling
    await _wait_for_pid(runner, status.pid)
    
    # Check final status
    proc_status = runner.get_process(status.pid)
    assert proc_status['status'] == 'completed'
    assert proc_status['return_code'] == 0

@pytest.mark.asyncio
async def test_get_process_log(runner):
    """Test retrieving process logs"""
    # Run a command
    status = await runner.fork("echo test_output", shell=True)
    
    # Wait for completion by polling
    await _wait_for_pid(runner, status.pid)
    
    # Get log content
    log_content = runner.get_process_log(status.pid)
    assert "test_output" in log_content
    # Verify log file exists in temp directory
    assert status.log_file.exists()
    assert status.log_file.parent == runner.log_dir

@pytest.mark.asyncio
async def test_failed_command_status(runner):
    """Test status tracking for failed commands"""
    # Run a command that will fail
    status = await runner.fork(
        "python",
        ["-c", "import sys; print('error', file=sys.stderr); sys.exit(1)"]
    )
    
    # Wait for completion by polling
    await _wait_for_pid(runner, status.pid)
    
    # Check status
    proc_status = runner.get_process(status.pid)
    assert proc_status['status'] == 'failed'
    assert proc_status['return_code'] == 1
    
    # Check log contains error
    log_content = runner.get_process_log(status.pid)
    assert "error" in log_content
    # Verify log file exists
    assert status.log_file.exists()

@pytest.mark.asyncio
async def test_multiple_active_processes(runner):
    """Test tracking multiple processes simultaneously"""
    # Start multiple commands
    cmd1 = await runner.fork("sleep 1" if sys.platform != "win32" else "timeout 1", shell=True)
    cmd2 = await runner.fork("sleep 2" if sys.platform != "win32" else "timeout 2", shell=True)
    
    await asyncio.sleep(0.1) # tick to allow the processes to start

    # Verify both commands have log files
    assert cmd1.log_file.exists()
    assert cmd2.log_file.exists()
    assert cmd1.log_file.parent == runner.log_dir
    assert cmd2.log_file.parent == runner.log_dir
    
    # Check both are tracked
    active = runner.get_active_processes()
    assert len(active) == 2
    assert cmd1.pid in active
    assert cmd2.pid in active
    
    # Wait for first command to finish by polling
    await _wait_for_pid(runner, cmd1.pid)
    
    # First command should be done, second still running
    assert runner.get_process(cmd1.pid)['status'] == 'completed'
    assert runner.get_process(cmd2.pid)['status'] == 'running'
    
    # Wait for second command by polling
    await _wait_for_pid(runner, cmd2.pid)
    
    assert runner.get_process(cmd2.pid)['status'] == 'completed'

@pytest.mark.asyncio
async def test_get_json_response(runner):
    """Test JSON response parsing"""
    # Run a command that outputs JSON
    status = await runner.fork(
        "python",
        ["-c", "import json; print(json.dumps({'key': 'value'}))"]
    )

    # Wait for completion by polling
    await _wait_for_pid(runner, status.pid)
    
    # Parse JSON response
    json_data = runner.get_json_response(status.pid)
    assert isinstance(json_data, dict)
    assert json_data['key'] == 'value'
    # Verify log file exists
    assert status.log_file.exists()
    assert status.log_file.parent == runner.log_dir

@pytest.mark.asyncio
async def test_command_sanitization(runner):
    """Test command sanitization and path traversal prevention"""
    # Test path traversal attempt in command
    with pytest.raises(CommandError):
        await runner.execute("../malicious")
        
    # Test path traversal in arguments
    with pytest.raises(CommandError):
        await runner.execute("echo", ["../../malicious"])

@pytest.mark.asyncio
async def test_env_and_cwd(runner):
    """Test environment variables and working directory handling"""
    # Test with custom environment variables
    env = {"TEST_VAR": "test_value"}
    output = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
    
    if sys.platform == "win32":
        status = await runner.execute("echo", ["%TEST_VAR%"], env=env, shell=True, status_callback=callback)
    else:
        status = await runner.execute("echo", ["$TEST_VAR"], env=env, shell=True, status_callback=callback)
    assert status.return_code == 0
    assert "test_value" in output[0]
    
    # Test with working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        status = await runner.execute("pwd" if sys.platform != "win32" else "cd", cwd=temp_dir, shell=True, status_callback=callback)
        assert status.return_code == 0
        assert temp_dir in output[-1]

@pytest.mark.asyncio
async def test_timeout_handling(runner):
    """Test timeout behavior for long-running commands"""
    # Test command that exceeds timeout
    with pytest.raises(asyncio.TimeoutError):
        await runner.execute("sleep" if sys.platform != "win32" else "timeout", ["10"], timeout=0.1)
    
    # Verify process is properly terminated after timeout
    await asyncio.sleep(0.2)  # Give time for cleanup
    # Could check process list to verify it's gone

@pytest.mark.asyncio
async def test_process_cleanup(runner):
    """Test proper process cleanup on errors and interruptions"""
    # Start a long-running process
    status = await runner.fork("sleep" if sys.platform != "win32" else "timeout", ["10"])
    
    # Force cleanup
    runner.kill_all_processes()
    
    # Verify process is terminated
    await asyncio.sleep(0.1)  # Give time for cleanup
    proc_status = runner.get_process(status.pid)
    assert proc_status['status'] != 'running'

def test_filename_sanitization(runner):
    """Test Windows filename sanitization"""
    # Test invalid characters - there are 9 invalid chars: < > : " / \ | ? *
    assert runner._sanitize_filename('test<>:"/\\|?*file.txt') == 'test_________file.txt'
    
    # Test reserved names
    assert runner._sanitize_filename('CON.txt') == '_CON.txt'
    assert runner._sanitize_filename('PRN.log') == '_PRN.log'

@pytest.mark.asyncio
async def test_stream_encoding(runner):
    """Test handling of different character encodings in output streams"""
    # Test non-ASCII output
    output = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
    
    # Echo a string with special characters
    status = await runner.execute(
        "python",
        ["-c", "print('Hello 世界')"],
        status_callback=callback
    )
    assert status.return_code == 0
    assert "Hello 世界" in output[0]

@pytest.mark.asyncio
async def test_error_stream_handling(runner):
    """Test proper handling of stderr output"""
    output = []
    errors = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
        if status.stderr:
            errors.append(status.stderr)
    
    # Command that writes to both stdout and stderr
    status = await runner.execute(
        "python",
        ["-c", "import sys; print('out'); print('err', file=sys.stderr)"],
        status_callback=callback
    )
    
    assert status.return_code == 0
    assert "out" in output[0]
    assert "err" in errors[0]
