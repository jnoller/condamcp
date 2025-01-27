"""
These are all local paths / files / directories:

	•	Recipe path: /Users/jesse/Code/conda-feedstocks/llama.cpp-feedstock
	•	Conda build config: /Users/jesse/Code/conda-feedstocks/conda_build_config.yaml
	•	Build root: /Users/jesse/Code/conda-feedstocks/builds
	•	Additional channel for the build: ai-staging
	•	Conda Environment: build

"""

"""Tests for AsyncCondaBuild class."""

import pytest
import pytest_asyncio
import pytest_timeout
import os
import asyncio
from pathlib import Path
import time
import logging
from typing import AsyncIterator
from condamcp.condabuild import AsyncCondaBuild
from condamcp.async_cmd import ProcessStatus

# Local paths for testing
RECIPE_PATH = "/Users/jesse/Code/conda-feedstocks/llama.cpp-feedstock"
CONFIG_FILE = "/Users/jesse/Code/conda-feedstocks/conda_build_config.yaml"
BUILD_ROOT = "/Users/jesse/Code/conda-feedstocks/builds"
CHANNEL = "ai-staging"
BUILD_ENV = "build"
BUILD_TIMEOUT = 1800  # 30 minutes

# Set up logger
logger = logging.getLogger(__name__)

@pytest_asyncio.fixture(scope="function")
async def conda_build() -> AsyncCondaBuild:
    """Fixture providing an AsyncCondaBuild instance for testing."""
    builder = AsyncCondaBuild(build_env=BUILD_ENV)
    try:
        yield builder
    finally:
        # Cleanup any running processes using the parent class's tracking
        for pid, status in builder.get_active_commands().items():
            if status.process and status.process.returncode is None:  # Only terminate if still running
                try:
                    status.process.terminate()
                except ProcessLookupError:
                    pass  # Process already finished

@pytest.mark.asyncio
@pytest.mark.timeout(2100)  # 35 minute timeout
async def test_conda_build_process(conda_build, caplog):
    """Test the full conda build process including status checking and log retrieval."""
    caplog.set_level(logging.INFO)
    
    try:
        # Validate required paths exist
        required_paths = {
            'Recipe': RECIPE_PATH,
            'Config file': CONFIG_FILE,
            'Build root': BUILD_ROOT
        }
        
        missing_paths = []
        for name, path in required_paths.items():
            exists = os.path.exists(path)
            logger.info(f"{name} path exists: {exists}")
            if not exists:
                missing_paths.append(f"{name}: {path}")
        
        if missing_paths:
            raise ValueError(f"Required paths do not exist:\n" + "\n".join(missing_paths))
        
        # Log command info before executing
        logger.info(f"Build environment: {BUILD_ENV}")
        logger.info(f"Recipe path exists: {os.path.exists(RECIPE_PATH)}")
        logger.info(f"Config file exists: {os.path.exists(CONFIG_FILE)}")
        logger.info(f"Build root exists: {os.path.exists(BUILD_ROOT)}")
        
        # Capture the command that will be run
        args = ["build", RECIPE_PATH]
        if CONFIG_FILE:
            args.extend(["--config-file", CONFIG_FILE])
        if BUILD_ROOT:
            args.extend(["--croot", BUILD_ROOT])
        if CHANNEL:
            args.extend(["-c", CHANNEL])
        
        # Show the full command including environment
        if BUILD_ENV:
            full_cmd = f"{conda_build.binary_path} run -n {BUILD_ENV} conda build {' '.join(args)}"
        else:
            full_cmd = f"{conda_build.binary_path} build {' '.join(args)}"
        logger.info(f"Full command to run: {full_cmd}")
        
        # Launch the build
        status = await conda_build.build(
            recipe_path=RECIPE_PATH,
            config_file=CONFIG_FILE,
            croot=BUILD_ROOT,
            channels=[CHANNEL]
        )
        
        logger.info("Initial process status:")
        logger.info(f"PID: {status.pid}")
        logger.info(f"Return code: {status.return_code}")
        logger.info(f"Error: {status.error if status.error else 'None'}")
        logger.info(f"Stdout: {status.stdout if status.stdout else 'None'}")
        logger.info(f"Stderr: {status.stderr if status.stderr else 'None'}")
        
        assert isinstance(status, ProcessStatus)
        assert status.pid > 0

        # Get build ID directly from status
        build_id = status.build_id
        assert build_id is not None

        # Check if process failed immediately
        build_status = await conda_build.check_build_status(build_id)
        logger.info(f"Initial build status: {build_status}")

        if build_status['return_code'] is not None:
            logger.error("Build failed immediately!")
            # Get log content
            log_content = conda_build.get_build_log(build_id)
            if log_content != "Build ID not found":
                logger.info(f"Log content:\n{log_content}")

            raise RuntimeError(f"Build failed with return code {build_status['return_code']}")

        # Wait for build to complete with timeout
        start_time = time.time()
        completed = False
        last_status = None
        
        while time.time() - start_time < BUILD_TIMEOUT:  # 30 minute timeout
            build_status = await conda_build.check_build_status(build_id)
            if build_status != last_status:  # Only print if status changed
                logger.info(f"Build status: {build_status}")
                last_status = build_status
                
                # If status changed to completed/failed, print logs
                if build_status['status'] in ['completed', 'failed']:
                    log_content = conda_build.get_build_log(build_id)
                    logger.info(f"Build log:\n{log_content}")
            
            if build_status['status'] in ['completed', 'failed']:
                completed = True
                break
                
            await asyncio.sleep(1)  # Check every second
        
        assert completed, "Build did not complete within timeout"
        
        # Get final status and logs
        final_status = await conda_build.check_build_status(build_id)
        log_content = conda_build.get_build_log(build_id)
        
        logger.info(f"Final build status: {final_status}")
        logger.info(f"Final log content:\n{log_content}")

        # Verify we have meaningful output
        assert len(log_content) > 0, "No build log was generated"
        if final_status['status'] == 'failed':
            raise RuntimeError(f"Build failed with return code {final_status['return_code']}")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise