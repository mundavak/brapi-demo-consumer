# MCP PDF Reader Installer Package 📚

## What This Does

This installer package sets up **PDF reading capabilities** for AI assistants in VS Code. After installation, you can ask GitHub Copilot to read, analyze, and summarize PDF files using natural language prompts like:

- *"Read the user manual PDF"*
- *"Summarize the research paper on trading"*  
- *"Extract text from the first 5 pages of guide.pdf"*
- *"List all available PDFs"*

## Quick Installation

1. **Download** this entire folder to your computer
2. **Double-click** `install.bat` 
3. **Follow prompts** to specify:
   - Where to install (e.g., `C:\MCPPDFReader`)
   - Your PDF folder (e.g., `D:\MyDocuments\PDFs`)
4. **Restart VS Code** when done
5. **Test**: Ask Copilot to "List available PDFs"

## Path Configuration Explained

### Installation Path
- **What**: Where the MCP system gets installed
- **Example**: `C:\MCPPDFReader` or `C:\Tools\MCPPDFReader`
- **Why**: Contains Python environment and server scripts
- **Tip**: Avoid spaces in the path

### PDF Source Path  
- **What**: Folder containing your PDF files
- **Example**: `D:\MyProject\Documents` or `C:\Users\YourName\PDFs`
- **Why**: Tells the system where to find your PDFs
- **Tip**: Can be any folder, even with subfolders

## Files Included

- `install.bat` - **Main installer** (just double-click this!)
- `Install-MCP-PDFReader.ps1` - PowerShell installer script
- `README.md` - Quick start guide  
- `MCP_PDF_Reader_Installation_Guide.md` - **Complete guide** (all details)
- `MCP_PDF_Reader_Installation_Guide.pdf` - Same guide as PDF
- `MANUAL_INSTALL.md` - Manual setup if auto-installer fails
- `pdf_reader_server.py` - MCP server implementation
- `vscode-settings-template.json` - Shows VS Code configuration

## Requirements

- **Python 3.8+** installed (check with `python --version`)
- **VS Code** with GitHub Copilot extension
- **Windows** with PowerShell

## Troubleshooting

If installation fails:

1. **Python not found?**
   - Install from https://python.org/downloads/
   - Ensure "Add to PATH" is checked during installation

2. **Permission errors?**
   - Right-click `install.bat` → "Run as administrator"

3. **PowerShell blocked?**
   - Run as Admin: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`

4. **Still having issues?**
   - See `MANUAL_INSTALL.md` for step-by-step setup
   - Read full guide: `MCP_PDF_Reader_Installation_Guide.pdf`

## After Installation

✅ **Test it works**: In VS Code, ask Copilot: *"List available PDFs"*

✅ **Use natural language**: *"Read the user guide"*, *"Summarize training-manual.pdf"*

✅ **PowerShell helpers** (optional): Load with `. .\pdf-helper.ps1`

## What Gets Configured

The installer automatically:
- Creates Python virtual environment with PDF reading packages
- Sets up MCP server for VS Code integration  
- Updates VS Code settings.json with your paths
- Creates helper scripts for PowerShell users
- Tests everything works

## Support

- **Full Guide**: `MCP_PDF_Reader_Installation_Guide.pdf` (complete documentation)
- **Quick Manual Setup**: `MANUAL_INSTALL.md` 
- **Configuration Help**: `vscode-settings-template.json`

---

**Ready to install?** Just double-click `install.bat` and follow the prompts! 🚀