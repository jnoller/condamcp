# condabuild.py 
"""
Conda build command wrapper that uses AsyncProcessRunner to build and execute conda build commands.
"""

import os
import time
from pathlib import Path
from typing import Callable, Optional, List, Dict, Union, Any
from .async_cmd import ProcessStatus
from .condacmd import AsyncCondaCmd

class AsyncCondaBuild(AsyncCondaCmd):
    def __init__(self, log_dir: Optional[str] = None, *args, **kwargs):
        """Initialize async conda build wrapper with default settings.
        
        Args:
            log_dir: Directory for build logs (default: system temp directory)
            *args: Additional positional arguments passed to AsyncCondaCmd
            **kwargs: Additional keyword arguments passed to AsyncCondaCmd
        """
        super().__init__(log_dir=log_dir, *args, **kwargs)
        self.default_args = [
            "--no-anaconda-upload",
            "--error-overlinking"
        ]

    async def _validate_build_env(self, build_env: str) -> str:
        """Validate that the build environment exists.
        
        Args:
            build_env: Name of conda environment containing conda-build
        """
        status = await self.env("list", as_json=True)
        await self.wait_for_command(status.pid)
        env_list = self.get_json_response(status.pid)
        if build_env not in env_list:
            raise ValueError(f"Build environment {build_env} not found")

    def _validate_paths(self, recipe_path: str, config_file: Optional[str] = None, croot: Optional[str] = None) -> List[str]:
        """Validate that all required paths exist.

        Args:
            recipe_path: Path to recipe directory
            config_file: Path to conda build config file
            croot: Build root directory

        Returns:
            list: List of error messages, empty if all paths are valid
        """
        errors = []
        paths_to_check = {
            'Recipe': Path(recipe_path),
            'Config': Path(config_file) if config_file else None,
            'Build root': Path(croot) if croot else None
        }

        for name, path in paths_to_check.items():
            if path is not None and not path.exists():
                errors.append(f"{name} path does not exist: {path}")

        return errors

    async def build(
        self,
        recipe_path: str,
        build_env: str,
        config_file: Optional[str] = None,
        croot: Optional[str] = None,
        channels: Optional[Union[str, List[str]]] = None,
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
        quiet: bool = False,
        status_callback: Optional[Callable[[ProcessStatus], None]] = None
    ) -> ProcessStatus:
        """Build a conda package using conda-build.

        Args:
            recipe_path: Path to recipe directory
            config_file: Path to conda build config file
            croot: Build root directory
            channels: Additional channels to search for packages
            variant_config_files: Additional variant config files
            exclusive_config_files: Exclusive config files
            python_version: Python version for build
            perl: Perl version for build
            numpy: NumPy version for build
            r_base: R version for build
            lua: Lua version for build
            bootstrap: Bootstrap version
            append_file: File to append to meta.yaml
            clobber_file: File to clobber meta.yaml
            old_build_string: Use old build string
            use_channeldata: Use channeldata from repodata
            variants: Additional variants to add
            check: Run package test
            no_include_recipe: Don't include recipe in package
            source: Only obtain/extract source
            test: Run package tests
            no_test: Don't run package tests
            build_only: Only run build
            post: Only run post-build logic
            test_run_post: Run post-test commands
            skip_existing: Skip builds of existing packages
            keep_old_work: Keep old work directory
            dirty: Keep build directory
            debug: Debug build
            token: Token for anaconda.org
            user: User for anaconda.org
            label: Label for anaconda.org
            no_force_upload: Don't force upload
            zstd_compression_level: ZSTD compression level
            password: Password for anaconda.org
            sign: Sign packages with gpg
            sign_with: GPG key to sign packages
            identity: GPG identity to sign packages
            repository: Repository to upload to
            no_activate: Don't activate build environment
            no_build_id: Don't generate build id
            build_id_pat: Build id pattern
            verify: Verify package
            no_verify: Don't verify package
            strict_verify: Strict package verification
            output_folder: Output folder
            no_prefix_length_fallback: Don't allow prefix length fallback
            prefix_length_fallback: Allow prefix length fallback
            prefix_length: Length of build prefix
            no_locking: Disable locking
            no_remove_work_dir: Don't remove work directory
            error_overlinking: Error on overlinking
            no_error_overlinking: Don't error on overlinking
            error_overdepending: Error on overdepending
            no_error_overdepending: Don't error on overdepending
            long_test_prefix: Use long test prefix
            no_long_test_prefix: Don't use long test prefix
            keep_going: Keep going on build failures
            cache_dir: Cache directory
            no_copy_test_source_files: Don't copy test source files
            merge_build_host: Merge build and host environments
            stats_file: Stats file
            extra_deps: Extra dependencies
            extra_meta: Extra metadata
            suppress_variables: Suppress variables
            use_local: Use local channel
            override_channels: Override channels
            repodata_fn: Repodata filenames
            experimental: Enable experimental features
            no_lock: Disable locking
            repodata_use_zst: Use zst repodata
            env: Environment variables
            quiet: Quiet output
            status_callback: Callback for process status updates

        Returns:
            ProcessStatus: Process status object
        """
        # Validate paths before starting build
        errors = self._validate_paths(recipe_path, config_file, croot)
        if errors:
            raise ValueError("\n".join(errors))
        
        # Validate build environment exists
        await self._validate_build_env(build_env)

        # Construct base args
        args = []
        if recipe_path:
            args.append(recipe_path)

        # Add config options
        if config_file:
            args.extend(["--config-file", config_file])
        if croot:
            args.extend(["--croot", croot])
        if channels:
            if isinstance(channels, str):
                args.extend(["-c", channels])
            else:
                for channel in channels:
                    args.extend(["-c", channel])
        if variant_config_files:
            for file in variant_config_files:
                args.extend(["--variant-config-file", file])
        if exclusive_config_files:
            for file in exclusive_config_files:
                args.extend(["--exclusive-config-file", file])

        # Add version specifications
        if python_version:
            args.extend(["--python", python_version])
        if perl:
            args.extend(["--perl", perl])
        if numpy:
            args.extend(["--numpy", numpy])
        if r_base:
            args.extend(["--R", r_base])
        if lua:
            args.extend(["--lua", lua])

        # Add build options
        if bootstrap:
            args.extend(["--bootstrap", bootstrap])
        if append_file:
            args.extend(["--append-file", append_file])
        if clobber_file:
            args.extend(["--clobber-file", clobber_file])
        if old_build_string:
            args.append("--old-build-string")
        if use_channeldata:
            args.append("--use-channeldata")
        if variants:
            args.extend(["--variants", variants])
        if check:
            args.append("--check")
        if no_include_recipe:
            args.append("--no-include-recipe")
        if source:
            args.append("--source")
        if test:
            args.append("--test")
        if no_test:
            args.append("--no-test")
        if build_only:
            args.append("--build-only")
        if post:
            args.append("--post")
        if test_run_post:
            args.append("--test-run-post")
        if skip_existing:
            args.append("--skip-existing")
        if keep_old_work:
            args.append("--keep-old-work")
        if dirty:
            args.append("--dirty")
        if debug:
            args.append("--debug")

        # Add upload options
        if token:
            args.extend(["--token", token])
        if user:
            args.extend(["--user", user])
        if label:
            args.extend(["--label", label])
        if no_force_upload:
            args.append("--no-force-upload")
        if zstd_compression_level is not None:
            args.extend(["--zstd-compression-level", str(zstd_compression_level)])
        if password:
            args.extend(["--password", password])
        if sign:
            args.extend(["--sign", sign])
        if sign_with:
            args.extend(["--sign-with", sign_with])
        if identity:
            args.extend(["--identity", identity])
        if repository:
            args.extend(["--repository", repository])

        # Add environment options
        if no_activate:
            args.append("--no-activate")
        if no_build_id:
            args.append("--no-build-id")
        if build_id_pat:
            args.extend(["--build-id-pat", build_id_pat])

        # Add verification options
        if verify:
            args.append("--verify")
        if no_verify:
            args.append("--no-verify")
        if strict_verify:
            args.append("--strict-verify")

        # Add output options
        if output_folder:
            args.extend(["--output-folder", output_folder])
        if no_prefix_length_fallback:
            args.append("--no-prefix-length-fallback")
        if prefix_length_fallback:
            args.append("--prefix-length-fallback")
        if prefix_length is not None:
            args.extend(["--prefix-length", str(prefix_length)])

        # Add locking and work directory options
        if no_locking:
            args.append("--no-locking")
        if no_remove_work_dir:
            args.append("--no-remove-work-dir")

        # Add error handling options
        if error_overlinking:
            args.append("--error-overlinking")
        if no_error_overlinking:
            args.append("--no-error-overlinking")
        if error_overdepending:
            args.append("--error-overdepending")
        if no_error_overdepending:
            args.append("--no-error-overdepending")

        # Add test prefix options
        if long_test_prefix:
            args.append("--long-test-prefix")
        if no_long_test_prefix:
            args.append("--no-long-test-prefix")

        # Add build behavior options
        if keep_going:
            args.append("--keep-going")
        if cache_dir:
            args.extend(["--cache-dir", cache_dir])
        if no_copy_test_source_files:
            args.append("--no-copy-test-source-files")
        if merge_build_host:
            args.append("--merge-build-host")
        if stats_file:
            args.extend(["--stats-file", stats_file])

        # Add extra dependencies and metadata
        if extra_deps:
            for dep in extra_deps:
                args.extend(["--extra-deps", dep])
        if extra_meta:
            for key, value in extra_meta.items():
                args.extend(["--extra-meta", f"{key}={value}"])

        # Add channel options
        if suppress_variables:
            args.append("--suppress-variables")
        if use_local:
            args.append("--use-local")
        if override_channels:
            args.append("--override-channels")
        if repodata_fn:
            for fn in repodata_fn:
                args.extend(["--repodata-fn", fn])

        # Add experimental options
        if experimental:
            args.extend(["--experimental", experimental])
        if no_lock:
            args.append("--no-lock")
        if repodata_use_zst is not None:
            args.append("--repodata-use-zst" if repodata_use_zst else "--no-repodata-use-zst")

        # Add default args
        args.extend(self.default_args)

        # Set up environment and command
        if build_env:
            # When using conda run, we need: conda run -n ENV conda build ARGS
            args = ["run", "-n", build_env, "conda", "build"] + args
        else:
            # Direct conda build: conda build ARGS
            args = ["build"] + args

        # Fork the build process
        cwd = os.path.dirname(config_file) if config_file else None
        status = await self.fork(
            self.binary_path,
            args,
            env=env,
            cwd=cwd,
            enable_logging=True
        )

        # Add build_id to status for reference
        build_id = f"{int(time.time())}_{os.path.basename(recipe_path)}"
        status.build_id = build_id

        return status

    async def check_build_status(self, build_id: str) -> Dict[str, Any]:
        """Check the current status of a build process.

        Args:
            build_id: The build ID returned from build()

        Returns:
            dict: Build status information including current state and return code if completed
        """
        # Find the process status with matching build_id
        for pid, status in self.get_active_commands().items():
            if hasattr(status, 'build_id') and status.build_id == build_id:
                # Use AsyncProcessRunner's status tracking
                cmd_status = self.get_command_status(pid)
                cmd_status['build_id'] = build_id  # Add build_id to response
                return cmd_status

        return {'status': 'not_found', 'build_id': build_id}

    def get_build_log(self, build_id: str, tail: Optional[int] = None) -> str:
        """Get the log output from a build process.

        Args:
            build_id: The build ID returned from build()
            tail: Number of lines to return from end of log (None for all)

        Returns:
            str: Build log output
        """
        # Find the process status with matching build_id
        for pid, status in self.get_active_commands().items():
            if hasattr(status, 'build_id') and status.build_id == build_id:
                # Use AsyncProcessRunner's log retrieval
                return self.get_command_log(pid, tail)

        return "Build ID not found"