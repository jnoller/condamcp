# condamcp

## Overview

condamcp is a collection of Model Context Protocol (MCP) server implementations that enable natural language interactions with the conda ecosystem. It bridges the gap between human intent and conda's powerful capabilities, making environment management, package building, and conda operations accessible to users of all skill levels.

## Vision

condamcp reimagines how users interact with conda:

* Transform conda from a complex CLI tool into an intelligent assistant
* Bridge the gap between human intent and technical execution
* Make conda's power accessible to everyone, regardless of CLI expertise
* Enable natural language automation of conda workflows
* Provide intelligent guidance for package building and debugging

## How It Works

Built on the Model Context Protocol (MCP) standard:

* Users express their intent in natural language
* AI agents interpret the intent and required conda operations
* MCP server translates intent into conda commands
* Real-time feedback and validation ensure successful execution

## MCP Servers Included

* `condamcp` - Conda MCP server  
* `condabuild` - Conda Build MCP server
* `sysinfo` - System information MCP server

### Conda MCP

The `Conda MCP` server is a wrapper around the `conda` command line tool. It enables natural language interactions with the `conda` command line tool.

Supported Commands:
* :white_check_mark: `conda env`: "list all of my conda environments"
* :white_check_mark: `conda create`: "create an environment called 'experiment' and install numpy and pandas"
* :white_check_mark: `conda remove`: "remove numpy and pandas from the 'experiment' environment"
* :white_check_mark: `conda help`: "can you summarize the help for conda build?"
* :white_check_mark: `conda list`: "list all packages in the 'experiment' environment"
* :white_check_mark: `conda clean`: "I am running out of disk space, please clean up my conda environments"
* :white_check_mark: `conda compare`: "compare the 'experiment' environment to the 'production' environment"
* :white_check_mark: `conda info`: "show me my conda info in json format"
* :white_check_mark: `conda search`: "find me the latest version of numpy"
* :white_check_mark: `conda run`: "run `python -m http.server` in the 'experiment' environment"
* :white_check_mark: `run_in_background`: "install jupyterlab in the 'experiment' environment and start a notebook server in the background"
* :white_check_mark: `conda export`: "export the 'experiment' environment to a YAML file in my '~/data' directory"
* :white_check_mark: `conda install`: "install numpy and pandas in the 'experiment' environment"
* :white_check_mark: `conda upgrade`: "upgrade all of my 'experiment' environment packages to the latest versions"

### Sysinfo MCP

The `Sysinfo MCP` server exposes local system information such as CPU, memory, OS, disks and GPUs. It enables you to ask questions about your system and get answers in natural language but more importantly it allows the Agent to get
system information to make better package, package building and conda environment management decisions and recommendations.

Supported Commands:
* :white_check_mark: `get_system_info`: "Please show me my local system information"
:white_check_mark: `get_nvidia_gpu_info`: "Please show me my NVIDIA GPU information"

When used with the Conda MCP server:

* :white_check_mark: "Can you recommend the fastest version of pytorch for my system?"


### Conda Build MCP

The `Conda Build MCP` server is a wrapper around the `conda build` command line tool. It enables you to build conda packages locally using natural language.

**THE CONDA BUILD MCP SERVER IS STILL IN PROGRESS**

Supported Commands:
**TBD**

Example `conda build` WIP prompt:
```

Please create a new package build environment called "llamabuild" and then build the llama.cpp package for me:

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
```



## Installation

You should have `conda` installed. 

```bash
git clone https://github.com/jnoller/condamcp.git
conda create -n condamcp pip
conda activate condamcp
pip install -e .
```

Modify your Claude Desktop Configuration file (claude_desktop_config.json) to launch the conda mcp server:

``` json
{
  "mcpServers": {
    ...
    "Sysinfo": {
      "command": "/opt/homebrew/anaconda3/bin/conda",
      "args": ["run", "-n", "condamcp", "--no-capture-output", "sysinfo"]
    },
    "Conda": {
      "command": "/opt/homebrew/anaconda3/bin/conda",
      "args": ["run", "-n", "condamcp", "--no-capture-output", "condamcp"]
    },
    "CondaBuild": {
      "command": "/opt/homebrew/anaconda3/bin/conda",
      "args": ["run", "-n", "condamcp", "--no-capture-output", "condabuild"]
    }
    ...
  }
}
```

## Debugging the MCP server with the MCP Inspector

You must have NPX installed:

```bash
npx @modelcontextprotocol/inspector <path to conda> run -n <conda env> --no-capture-output <entrypoint>
```

Example:

```bash
npx @modelcontextprotocol/inspector /opt/homebrew/anaconda3/bin/conda run -n condamcp --no-capture-output condamcp
```
