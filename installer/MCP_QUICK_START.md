# MCP Document Reader - Quick Reference

## 🚀 Three Ways to Use

### 1️⃣ Local Python (Recommended for Development)

```powershell
# Prerequisites
pip install pymupdf python-docx mcp

# VS Code setting
"doc-reader": {
  "command": "python",
  "args": ["installer/pdf_reader_server.py"]
}

# Usage in Copilot Chat
@doc-reader list documents
@doc-reader read "Bookmap-User-Guide-6-1.pdf" pages 1-5
```

### 2️⃣ Docker Container (Recommended for Production)

```powershell
# Build
.\installer\build_docker.ps1

# VS Code setting
"doc-reader-docker": {
  "command": "docker",
  "args": ["run", "--rm", "-i", ...]
}

# Usage in Copilot Chat
@doc-reader-docker list documents
@doc-reader-docker read "ICT-Mentorship-Month-1-Notes.pdf"
```

### 3️⃣ Docker Compose (Recommended for Always-On)

```powershell
# Start
docker-compose -f docker-compose.mcp.yml up -d

# View logs
docker logs -f mcp-doc-reader

# Stop
docker-compose -f docker-compose.mcp.yml down
```

## 📚 Available Documents

- **46 PDF files** in KnowledgeBase
- Key documents:
  - Bookmap User Guide (430196357-Bookmap-User-Guide-6-1.pdf)
  - ICT Mentorship Notes (443878056-ICT-Mentorship-Month-1-Notes.pdf)
  - Order Flow Trading Guide
  - Stops & Icebergs Detection
  - Spoofing Analysis

## 🔧 Commands

### Build & Test

```powershell
# Local test
python installer/test_mcp_direct.py

# Docker build
.\installer\build_docker.ps1

# Docker test
docker run --rm -v "F:/TradingAgent/.../KnowledgeBase:/knowledge-base:ro" `
  mcp-doc-reader:latest python test_mcp_direct.py
```

### VS Code Integration

1. Update `.vscode/settings.json` with MCP server config
2. Restart VS Code
3. Use `@doc-reader` or `@doc-reader-docker` in Copilot Chat

## ✅ Status

- ✅ Python dependencies installed
- ✅ Docker image built successfully
- ✅ Container tested and working
- ✅ VS Code settings configured
- ✅ 46 PDFs accessible in KnowledgeBase

## 📖 Documentation

- `installer/DOCKER_README.md` - Complete Docker setup guide
- `.github/copilot-instructions.md` - AI coding guidelines
- `installer/test_mcp_direct.py` - Direct function tests
- `installer/build_docker.ps1` - Build automation

## 🎯 Next Steps

**To enable in VS Code:**

1. Restart VS Code completely
2. Open Copilot Chat
3. Type: `@doc-reader list documents`
4. Start querying your documents!

**Pro Tips:**

- Use page ranges for large PDFs: `pages 1-10`
- Docker is slower on Windows but more isolated
- Local Python is faster for development
- Check logs if connection fails: `docker logs mcp-doc-reader`
