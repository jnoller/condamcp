import pytest
import asyncio
from pathlib import Path
from condamcp.async_cmd import AsyncProcessRunner, CommandError, ProcessStatus
from condamcp.condacmd import AsyncCondaCmd
import sys

@pytest.fixture
def runner():
    return AsyncProcessRunner()

@pytest.mark.asyncio
async def test_basic_command(runner):
    """Test basic command execution without shell"""
    output = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
    
    status = await runner.execute("echo", ["hello"], status_callback=callback)
    assert status.return_code == 0
    assert "hello" in output[0]
    assert not status.stderr

@pytest.mark.asyncio
async def test_shell_command(runner):
    """Test command execution with shell"""
    output = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
            
    runner_shell = AsyncProcessRunner(shell=True)
    status = await runner_shell.execute("echo", ["hello"], status_callback=callback)
    assert status.return_code == 0
    assert "hello" in output[0]
    assert not status.stderr

@pytest.mark.asyncio
async def test_shell_command_with_pipes(runner):
    """Test shell command with shell features like pipes"""
    output = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
            
    runner_shell = AsyncProcessRunner(shell=True)
    status = await runner_shell.execute("echo hello | grep hello", status_callback=callback)
    assert status.return_code == 0
    assert "hello" in output[0]
    assert not status.stderr

@pytest.mark.asyncio
async def test_single_log_file(tmp_path, runner):
    """Test logging command output to a single file"""
    runner = AsyncProcessRunner(log_dir=tmp_path)
    status = await runner.execute("echo", ["test output"])
    
    # Get the log file (should be named something like echo_*.log)
    log_files = list(tmp_path.glob("echo_*.log"))
    assert len(log_files) == 1
    
    # Verify log contents
    log_content = log_files[0].read_text()
    assert "test output" in log_content

@pytest.mark.asyncio
async def test_split_output_streams(tmp_path, runner):
    """Test logging stdout and stderr to separate files"""
    runner = AsyncProcessRunner(log_dir=tmp_path, split_output_streams=True)
    
    # Use shell to redirect some output to stderr
    if sys.platform == "win32":
        cmd = "(echo stdout) && (echo stderr >&2)"
    else:
        cmd = "echo stdout; echo stderr 1>&2"
    
    status = await runner.execute(cmd, shell=True)
    
    # Should have both stdout and stderr files
    stdout_files = list(tmp_path.glob("*_stdout.log"))
    stderr_files = list(tmp_path.glob("*_stderr.log"))
    assert len(stdout_files) == 1
    assert len(stderr_files) == 1
    
    # Verify contents
    stdout_content = stdout_files[0].read_text()
    stderr_content = stderr_files[0].read_text()
    assert "stdout" in stdout_content
    assert "stderr" in stderr_content

@pytest.mark.asyncio
async def test_command_timeout(runner):
    """Test that long running processes can be timed out"""
    with pytest.raises(asyncio.TimeoutError):
        # Use sleep command that should be interrupted
        if sys.platform == "win32":
            cmd = "timeout 10"
        else:
            cmd = "sleep 10"
        
        await runner.execute(cmd, shell=True, timeout=0.1)  # Short timeout to keep test fast 

@pytest.mark.asyncio
async def test_environment_variables(runner):
    """Test command execution with custom environment variables"""
    output = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
            
    env = {"TEST_VAR": "test_value"}
    status = await runner.execute("echo", ["$TEST_VAR" if sys.platform != "win32" else "%TEST_VAR%"], 
                            env=env, shell=True, status_callback=callback)
    assert status.return_code == 0
    assert "test_value" in output[0]

@pytest.mark.asyncio
async def test_working_directory(tmp_path, runner):
    """Test command execution in specific working directory"""
    output = []
    def callback(status: ProcessStatus):
        if status.stdout:
            output.append(status.stdout)
            
    status = await runner.execute("pwd" if sys.platform != "win32" else "cd", 
                            cwd=tmp_path, shell=True, status_callback=callback)
    assert status.return_code == 0
    assert str(tmp_path) in output[0]

@pytest.mark.asyncio
async def test_status_callback(runner):
    """Test status callback functionality"""
    status_updates = []
    
    def callback(status: ProcessStatus):
        # Only append if we get stdout or it's the final status
        if status.stdout or status.return_code is not None:
            status_updates.append(status)
    
    # Run a command that outputs multiple lines
    status = await runner.execute(
        "python",
        ["-c", "for i in range(3): print(f'line {i}')"],
        status_callback=callback
    )
    
    assert status.return_code == 0
    # Should get: 3 lines + final status = 4 updates
    assert len(status_updates) == 4
    
    # Get all output lines (excluding the final status)
    output_lines = [update.stdout for update in status_updates[:-1]]
    expected_lines = [f'line {i}' for i in range(3)]
    # Sort both lists to compare content regardless of order
    assert sorted(output_lines) == sorted(expected_lines)
    
    # Check final status
    assert status_updates[-1].stdout == ''
    assert status_updates[-1].stderr == ''
    assert status_updates[-1].return_code == 0

@pytest.mark.asyncio
async def test_command_validation(runner):
    """Test command validation prevents path traversal"""
    with pytest.raises(CommandError):
        await runner.execute("../some_command")

@pytest.mark.asyncio
async def test_nonexistent_command(runner):
    """Test handling of non-existent commands"""
    try:
        await runner.execute("nonexistentcommand123")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "No such file or directory" in str(e)
        assert "nonexistentcommand123" in str(e)

@pytest.mark.asyncio
async def test_shell_path_override(tmp_path):
    """Test using custom shell path"""
    shell_path = "/bin/bash" if sys.platform != "win32" else "cmd.exe"
    runner = AsyncProcessRunner(shell=True, shell_path=shell_path)
    status = await runner.execute("echo", ["hello"])
    assert status.return_code == 0

@pytest.mark.asyncio
async def test_combined_log_format(tmp_path):
    """Test combined log file format includes timestamps and stream labels"""
    import re
    runner = AsyncProcessRunner(log_dir=tmp_path, split_output_streams=False)
    status = await runner.execute("echo hello", shell=True)
    
    log_files = list(tmp_path.glob("*_output.log"))
    assert len(log_files) == 1
    
    log_content = log_files[0].read_text()
    # Check log format: [timestamp] [stream] content
    assert re.search(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[stdout\] hello', log_content)

@pytest.mark.asyncio
async def test_process_cleanup_after_timeout(runner):
    """Test that process is properly cleaned up after timeout"""
    import psutil
    
    with pytest.raises(asyncio.TimeoutError):
        if sys.platform == "win32":
            cmd = "timeout 10"
        else:
            cmd = "sleep 10"
        
        status = await runner.execute(cmd, shell=True, timeout=0.1)
    
    # Give a small delay for process cleanup
    await asyncio.sleep(0.1)
    
    # Verify no zombie processes are left
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    assert not any(proc.name() in ['sleep', 'timeout'] for proc in children) 

@pytest.mark.asyncio
async def test_python_command_with_stderr(tmp_path):
    """Test Python command execution with stderr output"""
    stdout = []
    stderr = []
    def callback(status: ProcessStatus):
        if status.stdout:
            stdout.append(status.stdout)
        if status.stderr:
            stderr.append(status.stderr)
            
    runner = AsyncProcessRunner(log_dir=tmp_path)
    status = await runner.execute(
        "python",
        ["-c", "import sys; print('Hello'); print('Error', file=sys.stderr)"],
        status_callback=callback
    )
    assert status.return_code == 0
    assert "Hello" in stdout[0]
    assert "Error" in stderr[0]

@pytest.mark.asyncio
async def test_sequential_commands(tmp_path):
    """Test running multiple commands in sequence with different output modes"""
    stdout1 = []
    stderr1 = []
    def callback1(status: ProcessStatus):
        if status.stdout:
            stdout1.append(status.stdout)
        if status.stderr:
            stderr1.append(status.stderr)
            
    # First with combined output
    runner = AsyncProcessRunner(log_dir=tmp_path, split_output_streams=False)
    status1 = await runner.execute(
        "python",
        ["-c", "print('Hello'); import sys; print('Error1', file=sys.stderr)"],
        status_callback=callback1
    )
    assert status1.return_code == 0
    assert "Hello" in stdout1[0]
    assert "Error1" in stderr1[0]
    
    stdout2 = []
    stderr2 = []
    def callback2(status: ProcessStatus):
        if status.stdout:
            stdout2.append(status.stdout)
        if status.stderr:
            stderr2.append(status.stderr)
            
    # Then with split output
    runner_split = AsyncProcessRunner(log_dir=tmp_path, split_output_streams=True)
    status2 = await runner_split.execute(
        "python",
        ["-c", "print('Hello2'); import sys; print('Error2', file=sys.stderr)"],
        status_callback=callback2
    )
    assert status2.return_code == 0
    assert "Hello2" in stdout2[0]
    assert "Error2" in stderr2[0]
    
    # Verify log files for both runs exist
    combined_logs = list(tmp_path.glob("python_*_output.log"))
    split_stdout_logs = list(tmp_path.glob("python_*_stdout.log"))
    split_stderr_logs = list(tmp_path.glob("python_*_stderr.log"))
    
    assert len(combined_logs) == 1
    assert len(split_stdout_logs) == 1
    assert len(split_stderr_logs) == 1

@pytest.mark.asyncio
async def test_logging_configuration(tmp_path, caplog):
    """Test that logging works correctly with different configurations"""
    import logging
    
    # Create a specific logger for this test
    logger = logging.getLogger("test_async_cmd")
    logger.setLevel(logging.INFO)
    
    # Configure file handler
    log_file = tmp_path / "async_process.log"
    file_handler = logging.FileHandler(str(log_file))
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)
    
    # Create a runner and track process updates
    updates = []
    def status_callback(status: ProcessStatus):
        updates.append(status)
        logger.info(f"Process {status.pid} status update")
    
    runner = AsyncProcessRunner(log_dir=tmp_path)
    
    # Run a command that generates both stdout and stderr
    with caplog.at_level(logging.INFO):
        status = await runner.execute(
            "python",
            ["-c", "print('Hello'); import sys; print('Error', file=sys.stderr)"],
            status_callback=status_callback
        )
    
    # Verify logging output
    assert any("status update" in record.message for record in caplog.records)
    assert log_file.exists()
    log_content = log_file.read_text()
    assert "status update" in log_content
    
    # Clean up
    logger.removeHandler(file_handler)
    file_handler.close()
