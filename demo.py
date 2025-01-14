from condamcp.condabuild import CondaBuild
import time
from pathlib import Path

def main():
    # Configure paths
    FEEDSTOCK_PATH = Path("/Users/jesse/Code/conda-feedstocks/llama.cpp-feedstock")
    BUILD_CONFIG = Path("/Users/jesse/Code/conda-feedstocks/conda_build_config.yaml")
    BUILD_ROOT = Path("/Users/jesse/Code/conda-feedstocks/builds")

    # Initialize conda build with specific build environment
    conda_build = CondaBuild(use_shell=True, build_env="build")

    # Start the llama.cpp build
    print("\nStarting llama.cpp conda build...")
    print(f"Recipe path: {FEEDSTOCK_PATH}")
    print(f"Config file: {BUILD_CONFIG}")
    print(f"Build root: {BUILD_ROOT}")
    
    try:
        build_id = conda_build.build(
            recipe_path=str(FEEDSTOCK_PATH),
            config_file=str(BUILD_CONFIG),
            channels=["ai-staging"],
            croot=str(BUILD_ROOT)
        )
        print(f"\nBuild started with ID: {build_id}")

        # Monitor build progress
        try:
            while True:
                # Get build status
                status = conda_build.get_build_status(build_id)
                print(f"\nBuild status: {status}")

                # Show recent log output
                log = conda_build.get_build_log(build_id, tail=10)
                print("\nRecent build output:")
                print(log)

                # Show full command on first iteration
                if 'command' in conda_build.active_builds.get(build_id, {}):
                    print("\nFull build command:")
                    print(conda_build.active_builds[build_id]['command'])

                # Exit if build is complete
                if status['status'] in ['completed', 'failed']:
                    print(f"\nBuild {status['status']}!")
                    print("\nFull build log:")
                    print(conda_build.get_build_log(build_id))
                    break

                # Wait before checking again
                print("\nWaiting 5 seconds...")
                time.sleep(5)

        except KeyboardInterrupt:
            print("\nBuild monitoring interrupted. Build is still running in background.")
            print(f"You can check status later with build ID: {build_id}")
            print("\nTo check status: conda_build.get_build_status('{build_id}')")
            print(f"To view logs: conda_build.get_build_log('{build_id}')")

    except ValueError as e:
        print(f"\nError starting build: {e}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    main()
