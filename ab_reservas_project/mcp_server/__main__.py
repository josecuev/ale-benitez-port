"""
Arranque del servicio MCP.

    python -m mcp_server                 # stdio (Claude Desktop / Claude Code)
    MCP_TRANSPORT=http python -m mcp_server   # HTTP remoto

Los tools no cambian entre transportes: solo cambia esta línea de arranque.
"""
import os

from .server import mcp

if __name__ == "__main__":
    transporte = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transporte == "http":
        mcp.run(
            transport="http",
            host=os.environ.get("MCP_HOST", "0.0.0.0"),
            port=int(os.environ.get("MCP_PORT", "8001")),
        )
    else:
        mcp.run()
