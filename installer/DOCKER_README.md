# MCP Document Reader - Docker Setup

## Overview

This Docker setup containerizes the MCP (Model Context Protocol) document reader server for reading PDFs, DOCX, and text files from the KnowledgeBase directory.

## Prerequisites

- Docker Desktop installed and running
- Windows with WSL2 (for Docker on Windows)
- PowerShell 5.1 or later

## Quick Start

### 1. Build the Docker Image

```powershell
# Run the build script
.\installer\build_docker.ps1
```

Or manually:

```powershell
docker build -t mcp-doc-reader:latest -f installer/Dockerfile installer/
```

### 2. Run with Docker Compose

```powershell
# Start the service
docker-compose -f docker-compose.mcp.yml up -d

# View logs
docker logs -f mcp-doc-reader

# Stop the service
docker-compose -f docker-compose.mcp.yml down
```

### 3. Run Standalone Container

```powershell
docker run --rm -i `
  -v "F:/TradingAgent/deaProjects/brapi-demo-consumer/KnowledgeBase:/knowledge-base:ro" `
  -e PDF_SOURCE_DIR=/knowledge-base `
  mcp-doc-reader:latest
```

## VS Code Integration

The `.vscode/settings.json` includes two MCP server configurations:

### Option 1: Local Python (Default)

```json
{
  "github.copilot.chat.mcpServers": {
    "doc-reader": {
      "command": "python",
      "args": ["installer/pdf_reader_server.py"]
    }
  }
}
```

### Option 2: Docker Container

```json
{
  "github.copilot.chat.mcpServers": {
    "doc-reader-docker": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v",
        "F:/TradingAgent/.../KnowledgeBase:/knowledge-base:ro",
        "mcp-doc-reader:latest"
      ]
    }
  }
}
```

To switch between them, restart VS Code and use:

- `@doc-reader` for local Python
- `@doc-reader-docker` for Docker container

## Testing

### Test the Docker Container

```powershell
# Test dependencies
docker run --rm mcp-doc-reader:latest python -c "import fitz, docx; print('OK')"

# Test document listing
docker run --rm -i `
  -v "F:/TradingAgent/deaProjects/brapi-demo-consumer/KnowledgeBase:/knowledge-base:ro" `
  mcp-doc-reader:latest python test_mcp_direct.py
```

### Test with MCP Client

After building the image, restart VS Code and test:

```
@doc-reader-docker list documents
@doc-reader-docker read "Bookmap-User-Guide-6-1.pdf" pages 1-3
```

## Volume Mounts

The container mounts KnowledgeBase as read-only:

```yaml
volumes:
  - ../KnowledgeBase:/knowledge-base:ro
```

**Benefits:**

- ✅ Prevents accidental file modifications
- ✅ Direct access to all PDFs/DOCX files
- ✅ No file copying needed
- ✅ Real-time updates when files are added

## Architecture

```
┌─────────────────────────────────────────┐
│          VS Code / Copilot              │
│     (GitHub Copilot Chat with MCP)      │
└───────────────┬─────────────────────────┘
                │ JSON-RPC over stdin/stdout
                ▼
┌─────────────────────────────────────────┐
│      Docker Container                   │
│  ┌─────────────────────────────────┐   │
│  │   pdf_reader_server.py          │   │
│  │   - PyMuPDF (PDF reading)       │   │
│  │   - python-docx (DOCX reading)  │   │
│  │   - MCP protocol handler        │   │
│  └─────────────────────────────────┘   │
│                │                        │
│                ▼                        │
│  /knowledge-base (mounted volume)      │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│    Host: KnowledgeBase Directory        │
│    (78+ PDFs, DOCX files)               │
└─────────────────────────────────────────┘
```

## Advantages of Docker Setup

1. **Isolation** - Dependencies don't conflict with system Python
2. **Portability** - Same environment on any machine
3. **Security** - Read-only access to documents
4. **Reproducibility** - Consistent behavior across deployments
5. **Easy Updates** - Rebuild image to update dependencies

## Troubleshooting

### Container won't start

```powershell
# Check Docker is running
docker ps

# View container logs
docker logs mcp-doc-reader

# Check volume mount
docker run --rm -v "F:/TradingAgent/.../KnowledgeBase:/knowledge-base:ro" `
  mcp-doc-reader:latest ls -la /knowledge-base
```

### VS Code can't connect

```powershell
# Rebuild the image
.\installer\build_docker.ps1

# Restart VS Code completely
# Ensure Docker Desktop is running
```

### Performance issues

- Docker on Windows uses WSL2 - ensure it's properly configured
- Consider using native Python if container is slow
- Check Docker Desktop resource allocation (Settings → Resources)

## Files

- `installer/Dockerfile` - Container image definition
- `installer/pdf_reader_server.py` - MCP server implementation
- `installer/requirements.txt` - Python dependencies
- `docker-compose.mcp.yml` - Docker Compose configuration
- `installer/build_docker.ps1` - Build automation script
- `.vscode/settings.json` - VS Code MCP integration

## Next Steps

1. ✅ Build the Docker image
2. ✅ Test with `test_mcp_direct.py`
3. ✅ Restart VS Code
4. ✅ Query documents with `@doc-reader-docker`
5. 🎯 Enjoy AI-powered document analysis!
