# condamcp
A Model Context Protocol Server for working with Conda

## Installation

You should have `conda` and [`conda-project`](https://conda-incubator.github.io/conda-project/user_guide.html) installed. 

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
    "Conda": {
      "command": "/opt/homebrew/anaconda3/bin/conda",
      "args": ["run", "-n", "condamcp", "--no-capture-output", "condamcp"]
    }
    ...
  }
}
```

Example `conda build` prompt:
```

Please build the llama.cpp package for me using the following options:

*	Recipe path: /Users/jesse/Code/conda-feedstocks/llama.cpp-feedstock
*	Conda build config: /Users/jesse/Code/conda-feedstocks/conda_build_config.yaml
*	Build root: /Users/jesse/Code/conda-feedstocks/builds
*	Additional channel for the build: ai-staging
*	Conda Environment: build

This package generates 3 different packages:

*	gguf
*	llama.cpp-tools
*	llama.cpp

If the build fails, please show me the logs and suggest a possible solution.
Please continue to monitor the build output until all packages are built.
If the build succeeds, please tell me what directory to open to access the files.
```