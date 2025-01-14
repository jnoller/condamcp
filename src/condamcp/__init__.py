from . import server

def run_mcp_server():
    """Entry point for the MCP server"""
    server.mcp.run()

__all__ = ['run_mcp_server', 'server']
