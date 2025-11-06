# Quick Manual Installation Guide

If the automated installer doesn't work, follow these manual steps:

## Step 1: Create Installation Directory
```powershell
mkdir C:\MCPPDFReader
cd C:\MCPPDFReader
```

## Step 2: Setup Python Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install PyMuPDF mcp
```

## Step 3: Create MCP Server Script
Create `pdf_reader_server.py` with the content from the installer package.

## Step 4: Update VS Code Settings
Add this to your VS Code settings.json:
```json
{
  "github.copilot.chat.mcpServers": {
    "pdf-reader": {
      "command": "C:\\MCPPDFReader\\venv\\Scripts\\python.exe",
      "args": ["C:\\MCPPDFReader\\pdf_reader_server.py"],
      "env": {
        "PDF_SOURCE_DIR": "YOUR_PDF_FOLDER_PATH",
        "PYTHONPATH": "C:\\MCPPDFReader"
      }
    }
  }
}
```

## Step 5: Test Installation
```powershell
$env:PDF_SOURCE_DIR = "YOUR_PDF_FOLDER_PATH"
C:\MCPPDFReader\venv\Scripts\python.exe C:\MCPPDFReader\pdf_reader_server.py list_pdfs
```

## Step 6: Restart VS Code
Completely restart VS Code for MCP changes to take effect.