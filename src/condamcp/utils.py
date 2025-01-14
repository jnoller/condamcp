"""Utility functions for conda command handling."""

import os
import platform
import shutil

def get_default_shell():
    """Get the default shell path for the current system."""
    if platform.system() == "Windows":
      # Windows is not supported yet
      raise NotImplementedError("Windows is not supported yet")
    
    # For Unix-like systems
    shell = os.environ.get("SHELL")
    if shell and os.path.exists(shell):
        return shell
    
    # Try common Unix shells in order of preference
    for shell in ["/bin/bash", "/bin/sh", "/bin/zsh"]:
        if os.path.exists(shell):
            return shell
    
    raise RuntimeError("No suitable shell found")

def get_default_conda_binary():
    """Get the default conda binary path."""
    # First try the standard PATH search
    conda_path = shutil.which("conda")
    if conda_path:
        # Convert condabin paths to main binary path
        if 'condabin' in conda_path:
            conda_path = conda_path.replace('condabin', 'bin')
        return conda_path
    
    # If that fails, try common conda installation locations
    common_paths = [
        "/opt/homebrew/anaconda3/bin/conda",  # Homebrew Anaconda
        "/opt/homebrew/Caskroom/miniconda/base/bin/conda",  # Homebrew Miniconda
        "/usr/local/anaconda3/bin/conda",  # Standard Anaconda
        "/usr/local/bin/conda",  # System-wide conda
        os.path.expanduser("~/anaconda3/bin/conda"),  # User Anaconda
        os.path.expanduser("~/miniconda3/bin/conda"),  # User Miniconda
    ]
    
    for path in common_paths:
        if os.path.isfile(path):
            return path
            
    raise RuntimeError(
        "Conda binary not found. Please ensure conda is installed and in PATH, "
        "or set CONDA_EXE environment variable."
    ) 

def get_conda_activation_commands():
    """Get the commands needed to initialize conda in a shell."""
    conda_prefix = os.path.dirname(os.path.dirname(get_default_conda_binary()))
    return [
        f'source "{conda_prefix}/etc/profile.d/conda.sh"',
        'conda deactivate'  # Start from base environment
    ] 