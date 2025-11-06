# MCP PDF Reader Installer Package

This package contains everything needed to set up PDF reading capabilities for VS Code AI assistants.

## Contents

- `install.bat` - Windows batch installer (double-click to run)
- `Install-MCP-PDFReader.ps1` - PowerShell installer script  
- `pdf_reader_server.py` - MCP server implementation
- `vscode-settings-template.json` - VS Code configuration template
- `MANUAL_INSTALL.md` - Manual installation instructions
- `MCP_PDF_Reader_Installation_Guide.md` - Complete installation guide
- `README.md` - This file

## Quick Start

1. **Double-click `install.bat`** to run the automated installer
2. **Follow the prompts** to specify installation and PDF paths
3. **Restart VS Code** after installation completes
4. **Test with AI**: "Read the first PDF in my collection"

## Requirements

- Python 3.8+ (in PATH)
- VS Code with GitHub Copilot
- PowerShell execution policy allowing scripts

## Installation Paths

During installation, you'll specify:

- **Installation Directory**: Where to install MCP PDF Reader (e.g., `C:\MCPPDFReader`)
- **PDF Source Directory**: Folder containing your PDF files (e.g., `D:\MyProject\PDFs`)

## After Installation

The installer will:
- ✅ Create Python virtual environment with required packages
- ✅ Install MCP server script
- ✅ Update VS Code settings.json with MCP configuration  
- ✅ Create helper PowerShell functions
- ✅ Test the installation

## Troubleshooting

If installation fails:
1. Check Python is installed: `python --version`
2. Ensure PowerShell can run scripts: `Get-ExecutionPolicy`
3. Run installer as Administrator if needed
4. See `MANUAL_INSTALL.md` for manual setup

## Usage Examples

After installation, try these with your AI assistant:

- "Read the user manual PDF"
- "Extract text from research-paper.pdf"  
- "List all available PDFs"
- "Summarize the trading guide"

## Support

- Full installation guide: `MCP_PDF_Reader_Installation_Guide.md`
- Manual setup: `MANUAL_INSTALL.md`
- Configuration template: `vscode-settings-template.json`

---

**Note**: This installer configures paths specifically for your system. Your friend will need to specify their own installation and PDF directories during setup.