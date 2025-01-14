# condamcp
A Model Context Protocol Server for working with Conda

## Installation

```bash
git clone https://github.com/jnoller/condamcp.git
cd condamcp
conda create -n condamcp python=3.10 pip
pip install -e .
```

By default, `condamcp` installs the `mcp` and `mcp[cli]` packages into its own environment.