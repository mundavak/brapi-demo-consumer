# MCP PDF Reader Installation Guide

## Overview

This installer sets up **Model Context Protocol (MCP) PDF Reader** for VS Code, enabling AI assistants (like GitHub Copilot) to read and analyze PDF files directly. This is particularly useful for projects with documentation, research papers, or knowledge bases stored as PDFs.

## What This Does

The installer configures:
1. **MCP Server**: A Python-based server that can extract text from PDFs
2. **VS Code Integration**: Configures GitHub Copilot to use the PDF reading capability  
3. **Helper Scripts**: PowerShell functions for easy PDF access
4. **Virtual Environment**: Isolated Python environment with required packages

## Prerequisites

Before running the installer, ensure you have:

- **Python 3.8 or higher** installed and available in PATH
  - Test with: `python --version`
  - Download from: https://python.org/downloads/
- **VS Code** installed with GitHub Copilot extension
- **PowerShell** execution policy allowing scripts
  - Run as Administrator: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

## Installation Options

### Option 1: Automated Installation (Recommended)

1. **Download** the installer package to your computer
2. **Right-click** on `install.bat` and select "Run as administrator" (if needed)
3. **Follow the prompts** to specify:
   - Installation directory (e.g., `C:\MCPPDFReader`)
   - Project path with PDFs (e.g., `D:\MyProject\KnowledgeBase`)

### Option 2: PowerShell Installation

1. Open **PowerShell as Administrator**
2. Navigate to the installer folder
3. Run: `.\Install-MCP-PDFReader.ps1 -InstallPath "C:\MCPPDFReader" -ProjectPath "D:\YourProject"`

### Option 3: Manual Installation

See `MANUAL_INSTALL.md` for step-by-step manual setup instructions.

## Path Configuration

You will need to specify two important paths during installation:

### Installation Path
- **What it is**: Where the MCP PDF Reader will be installed
- **Example**: `C:\MCPPDFReader` or `C:\Tools\MCPPDFReader`
- **Why needed**: Contains Python virtual environment and server scripts
- **Recommendation**: Use a path without spaces, on your main drive

### Project Path (PDF Source Directory)
- **What it is**: Folder containing your PDF files
- **Example**: `D:\MyProject\KnowledgeBase` or `C:\Documents\Research\PDFs`
- **Why needed**: Tells the MCP server where to find your PDFs
- **Recommendation**: Choose the main folder containing all PDFs you want to access

## What Gets Installed

The installer creates this structure:

```
Installation Directory (e.g., C:\MCPPDFReader\)
├── venv\                          # Python virtual environment
│   ├── Scripts\
│   │   ├── python.exe            # Python executable for MCP
│   │   └── Activate.ps1          # Environment activation
│   └── Lib\                      # Installed packages
├── pdf_reader_server.py          # MCP server script
└── README.txt                    # Installation notes

Project Directory (your PDF folder)
├── pdf-helper.ps1                # PowerShell helper functions
├── your-pdfs.pdf                 # Your existing PDFs
└── ...

VS Code Settings
└── settings.json                 # Updated with MCP configuration
```

## VS Code Configuration

The installer automatically adds this configuration to your VS Code `settings.json`:

```json
{
  "github.copilot.chat.mcpServers": {
    "pdf-reader": {
      "command": "C:\\MCPPDFReader\\venv\\Scripts\\python.exe",
      "args": ["C:\\MCPPDFReader\\pdf_reader_server.py"],
      "env": {
        "PDF_SOURCE_DIR": "D:\\YourProject\\KnowledgeBase",
        "PYTHONPATH": "C:\\MCPPDFReader"
      }
    }
  }
}
```

### Important Notes:
- **Backslashes are doubled** in JSON configuration
- **PDF_SOURCE_DIR** points to your project folder with PDFs
- **PYTHONPATH** points to the installation directory
- These paths are automatically configured by the installer

## Using the PDF Reader

### With AI Assistant (Natural Language)

After installation and VS Code restart, you can use these prompts:

- **"Read the trading guide PDF"** - AI will search for and read matching PDF
- **"Extract text from the first 5 pages of user-manual.pdf"** - Specific page range
- **"List all available PDFs"** - Shows all PDFs in your source directory
- **"Summarize the research paper on market analysis"** - AI reads and summarizes

### With PowerShell Helper Functions

Load the helper functions:
```powershell
. .\pdf-helper.ps1
```

Then use these commands:
```powershell
Read-PDF "trading"           # Find and read PDFs matching "trading"
Read-AllPDFs                # Extract text from all PDFs
Get-PDFList                 # List available PDFs
```

### Direct MCP Commands

For advanced users:
```powershell
# Set environment
$env:PDF_SOURCE_DIR = "D:\YourProject\KnowledgeBase"

# List PDFs
C:\MCPPDFReader\venv\Scripts\python.exe C:\MCPPDFReader\pdf_reader_server.py list_pdfs

# Extract specific PDF
C:\MCPPDFReader\venv\Scripts\python.exe C:\MCPPDFReader\pdf_reader_server.py extract_pdf_text filename.pdf
```

## Troubleshooting

### Common Issues and Solutions

#### "Python not found"
- **Problem**: Python not installed or not in PATH
- **Solution**: Install Python from python.org, ensure "Add to PATH" is checked during installation

#### "VS Code settings not found"  
- **Problem**: VS Code not installed or using different profile
- **Solution**: Install VS Code, or check that settings.json exists in `%APPDATA%\Code\User\`

#### "PDFs not found"
- **Problem**: Incorrect PDF_SOURCE_DIR path
- **Solution**: Check the path in VS Code settings.json, ensure it points to folder containing PDFs

#### "MCP server not responding"
- **Problem**: Virtual environment or packages not installed correctly
- **Solution**: Reinstall, check Python version compatibility, ensure PyMuPDF installed

#### "Permission denied" errors
- **Problem**: Installation directory requires admin rights
- **Solution**: Run installer as Administrator, or choose different installation path

### Testing Your Installation

1. **Check Python environment**:
   ```powershell
   C:\MCPPDFReader\venv\Scripts\python.exe --version
   ```

2. **Test MCP server**:
   ```powershell
   $env:PDF_SOURCE_DIR = "D:\YourProject\KnowledgeBase"
   C:\MCPPDFReader\venv\Scripts\python.exe C:\MCPPDFReader\pdf_reader_server.py list_pdfs
   ```

3. **Verify VS Code integration**: 
   - Restart VS Code completely
   - Open GitHub Copilot chat
   - Try: "List available PDFs"

### Logs and Debugging

- **VS Code Developer Console**: Press `Ctrl+Shift+I` to see MCP communication
- **Python errors**: Check terminal output when running MCP commands
- **PowerShell errors**: Check execution policy and file paths

## Updating Paths Later

If you need to change the PDF source directory or installation location:

### Update PDF Source Directory

1. **Edit VS Code settings.json**:
   - Open VS Code settings (Ctrl+,)
   - Search for "mcpServers"
   - Edit the "PDF_SOURCE_DIR" value

2. **Update helper scripts**:
   - Edit `pdf-helper.ps1` in your project directory
   - Change the `$KNOWLEDGE_BASE` variable

### Move Installation Directory

1. **Copy the entire installation folder** to new location
2. **Update VS Code settings.json**:
   - Change "command" path to new python.exe location
   - Change "args" path to new server script location
   - Change "PYTHONPATH" to new installation directory

## Security Considerations

- **Python Environment**: Installation creates isolated virtual environment
- **File Access**: MCP server only accesses PDFs in specified directory
- **VS Code Integration**: Uses standard MCP protocol, no additional permissions required
- **Network**: No network access required, works entirely locally

## Advanced Configuration

### Multiple PDF Directories

To access PDFs from multiple folders, you can:

1. **Create symbolic links** pointing to your main PDF directory
2. **Copy PDFs** to the main source directory
3. **Create multiple MCP servers** with different configurations

### Custom Page Ranges

When requesting PDF extraction, specify page ranges:
- `"all"` - Extract all pages (default)
- `"1-5"` - Extract pages 1 through 5
- `"10"` - Extract only page 10

### Performance Optimization

For large PDF collections:
- **Use specific filenames** rather than searching all PDFs
- **Extract specific page ranges** instead of entire documents
- **Consider SSD storage** for PDF directories

## Uninstallation

To remove the MCP PDF Reader:

1. **Remove VS Code configuration**:
   - Delete the "pdf-reader" section from settings.json mcpServers

2. **Delete installation directory**:
   - Remove the entire installation folder (e.g., `C:\MCPPDFReader`)

3. **Remove helper scripts**:
   - Delete `pdf-helper.ps1` from your project directory

## Support and Further Reading

### Documentation References
- **Model Context Protocol**: https://modelcontextprotocol.io/
- **PyMuPDF Documentation**: https://pymupdf.readthedocs.io/
- **VS Code Settings**: https://code.visualstudio.com/docs/getstarted/settings

### Common Use Cases
- **Research Projects**: Extract text from academic papers for analysis
- **Documentation**: Search through technical manuals and guides  
- **Knowledge Bases**: Access information from PDF collections
- **Legal Documents**: Extract text from contracts and legal files

### Performance Expectations
- **Small PDFs** (< 10 pages): Near-instant extraction
- **Medium PDFs** (10-100 pages): 1-5 seconds
- **Large PDFs** (100+ pages): 5-30 seconds depending on content
- **Bulk Operations**: Process multiple PDFs sequentially

---

## Installation Summary

This installer provides a complete solution for PDF reading in VS Code AI assistants. The key components work together to enable natural language PDF access:

1. **MCP Server** handles PDF text extraction using PyMuPDF
2. **VS Code Integration** connects AI assistants to the MCP server
3. **Helper Scripts** provide convenient PowerShell functions
4. **Automated Setup** handles all configuration and testing

After installation, simply restart VS Code and start asking your AI assistant to read PDFs using natural language prompts. The system will automatically find, extract, and provide PDF content for analysis.

For any issues or questions, refer to the troubleshooting section or check the manual installation guide for step-by-step debugging.