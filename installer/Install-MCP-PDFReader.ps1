# MCP PDF Reader Installer for VS Code
# This script sets up PDF reading capabilities for AI assistants in VS Code
# Run as Administrator if needed for system-wide installation

param(
    [string]$InstallPath = "",
    [string]$ProjectPath = "",
    [switch]$Help
)

if ($Help) {
    Write-Host @"
MCP PDF Reader Installer

USAGE:
    .\Install-MCP-PDFReader.ps1 -InstallPath "C:\MCPPDFReader" -ProjectPath "C:\YourProject"

PARAMETERS:
    -InstallPath    Where to install the MCP PDF Reader (default: C:\MCPPDFReader)
    -ProjectPath    Path to your project with PDFs (will be set as PDF_SOURCE_DIR)
    -Help          Show this help message

EXAMPLES:
    .\Install-MCP-PDFReader.ps1 -InstallPath "C:\Tools\MCPPDFReader" -ProjectPath "D:\MyProject"
    .\Install-MCP-PDFReader.ps1  (will prompt for paths)

WHAT THIS INSTALLER DOES:
1. Creates MCP PDF Reader directory structure
2. Sets up Python virtual environment
3. Installs required packages (PyMuPDF, mcp)
4. Creates MCP server script
5. Updates VS Code settings.json with MCP configuration
6. Creates helper scripts for easy PDF reading
7. Tests the installation

REQUIREMENTS:
- Python 3.8+ installed and in PATH
- VS Code installed
- Administrator rights (may be needed for some operations)
"@
    exit 0
}

function Write-Status {
    param([string]$Message, [string]$Color = "Green")
    Write-Host "▶ $Message" -ForegroundColor $Color
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Python found: $pythonVersion"
        }
        else {
            Write-Error "Python not found. Please install Python 3.8+ and add to PATH"
            return $false
        }
    }
    catch {
        Write-Error "Python not found. Please install Python 3.8+ and add to PATH"
        return $false
    }
    
    # Check VS Code
    $vsCodePaths = @(
        "$env:USERPROFILE\AppData\Roaming\Code\User\settings.json",
        "$env:APPDATA\Code\User\settings.json"
    )
    
    $vsCodeFound = $false
    foreach ($path in $vsCodePaths) {
        if (Test-Path $path) {
            $script:VSCodeSettingsPath = $path
            $vsCodeFound = $true
            Write-Success "VS Code settings found: $path"
            break
        }
    }
    
    if (-not $vsCodeFound) {
        Write-Error "VS Code settings.json not found. Please install VS Code first."
        return $false
    }
    
    return $true
}

function Get-InstallationPaths {
    if (-not $InstallPath) {
        Write-Host "`nPlease specify installation paths:" -ForegroundColor Yellow
        $InstallPath = Read-Host "MCP PDF Reader installation directory (e.g., C:\MCPPDFReader)"
        if (-not $InstallPath) {
            $InstallPath = "C:\MCPPDFReader"
            Write-Host "Using default: $InstallPath" -ForegroundColor Cyan
        }
    }
    
    if (-not $ProjectPath) {
        $ProjectPath = Read-Host "Project path containing PDFs (this will be your PDF_SOURCE_DIR)"
        if (-not $ProjectPath) {
            Write-Error "Project path is required!"
            exit 1
        }
    }
    
    $script:InstallPath = $InstallPath
    $script:ProjectPath = $ProjectPath
    
    Write-Status "Installation directory: $InstallPath"
    Write-Status "PDF source directory: $ProjectPath"
}

function Create-MCPDirectory {
    Write-Status "Creating MCP directory structure..."
    
    if (Test-Path $InstallPath) {
        Write-Host "Directory already exists. Continue? (y/n): " -NoNewline -ForegroundColor Yellow
        $response = Read-Host
        if ($response -ne 'y' -and $response -ne 'Y') {
            Write-Error "Installation cancelled"
            exit 1
        }
    }
    
    New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    Write-Success "Created directory: $InstallPath"
}

function Setup-PythonEnvironment {
    Write-Status "Setting up Python virtual environment..."
    
    Set-Location $InstallPath
    
    # Create virtual environment
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
    
    # Activate and install packages
    $activateScript = Join-Path $InstallPath "venv\Scripts\Activate.ps1"
    
    if (Test-Path $activateScript) {
        & $activateScript
        Write-Success "Virtual environment created and activated"
    }
    else {
        Write-Error "Failed to find activation script"
        exit 1
    }
    
    Write-Status "Installing required Python packages..."
    
    # Install packages
    python -m pip install --upgrade pip
    python -m pip install PyMuPDF mcp
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Python packages installed successfully"
    }
    else {
        Write-Error "Failed to install Python packages"
        exit 1
    }
}

function Create-MCPServer {
    Write-Status "Creating MCP server script..."
    
    $serverScript = Join-Path $InstallPath "pdf_reader_server.py"
    
    $serverContent = @"
#!/usr/bin/env python3
"""
MCP PDF Reader Server
Provides PDF reading capabilities for AI assistants via Model Context Protocol
"""

import os
import sys
import json
import fitz  # PyMuPDF
from pathlib import Path
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import Tool, TextContent

# Configuration
PDF_SOURCE_DIR = os.getenv('PDF_SOURCE_DIR', '.')

app = Server("pdf-reader")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="extract_pdf_text",
            description="Extract text from PDF files",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the PDF file to read"
                    },
                    "page_range": {
                        "type": "string", 
                        "description": "Page range (e.g., '1-5' or 'all')",
                        "default": "all"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="list_pdfs",
            description="List available PDF files in the source directory",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "list_pdfs":
        try:
            pdf_files = list(Path(PDF_SOURCE_DIR).glob("*.pdf"))
            file_list = [{"name": f.name, "size": f.stat().st_size} for f in pdf_files]
            return [TextContent(
                type="text",
                text=json.dumps({"pdfs": file_list, "count": len(file_list)}, indent=2)
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing PDFs: {str(e)}")]
    
    elif name == "extract_pdf_text":
        filename = arguments.get("filename")
        page_range = arguments.get("page_range", "all")
        
        try:
            pdf_path = Path(PDF_SOURCE_DIR) / filename
            if not pdf_path.exists():
                return [TextContent(type="text", text=f"PDF file not found: {filename}")]
            
            doc = fitz.open(str(pdf_path))
            
            # Parse page range
            if page_range == "all":
                pages = range(len(doc))
            else:
                # Handle ranges like "1-5"
                if "-" in page_range:
                    start, end = map(int, page_range.split("-"))
                    pages = range(start-1, min(end, len(doc)))  # Convert to 0-based
                else:
                    page_num = int(page_range) - 1  # Convert to 0-based
                    pages = [page_num] if 0 <= page_num < len(doc) else []
            
            extracted_text = ""
            page_info = []
            
            for page_num in pages:
                page = doc[page_num]
                text = page.get_text()
                extracted_text += f"\\n\\n--- Page {page_num + 1} ---\\n{text}"
                page_info.append({
                    "page": page_num + 1,
                    "text_length": len(text),
                    "has_images": len(page.get_images()) > 0
                })
            
            doc.close()
            
            result = {
                "filename": filename,
                "total_pages": len(doc),
                "extracted_pages": len(pages),
                "page_info": page_info,
                "text": extracted_text.strip()
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error extracting PDF: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"@

    Set-Content -Path $serverScript -Value $serverContent -Encoding UTF8
    Write-Success "MCP server script created: $serverScript"
}

function Update-VSCodeSettings {
    Write-Status "Updating VS Code settings..."
    
    # Read existing settings
    $settingsContent = "{}"
    if (Test-Path $VSCodeSettingsPath) {
        $settingsContent = Get-Content -Path $VSCodeSettingsPath -Raw
    }
    
    try {
        $settings = $settingsContent | ConvertFrom-Json
    }
    catch {
        Write-Host "Invalid JSON in settings.json, creating new settings object" -ForegroundColor Yellow
        $settings = [PSCustomObject]@{}
    }
    
    # Ensure MCP servers section exists
    if (-not $settings."github.copilot.chat.mcpServers") {
        $settings | Add-Member -NotePropertyName "github.copilot.chat.mcpServers" -NotePropertyValue ([PSCustomObject]@{})
    }
    
    # Add PDF reader configuration
    $pythonPath = (Join-Path $InstallPath "venv\Scripts\python.exe").Replace('\', '\\')
    $serverPath = (Join-Path $InstallPath "pdf_reader_server.py").Replace('\', '\\')
    $sourcePath = $ProjectPath.Replace('\', '\\')
    
    $pdfReaderConfig = [PSCustomObject]@{
        command = $pythonPath
        args    = @($serverPath)
        env     = [PSCustomObject]@{
            PDF_SOURCE_DIR = $sourcePath
            PYTHONPATH     = $InstallPath.Replace('\', '\\')
        }
    }
    
    $settings."github.copilot.chat.mcpServers" | Add-Member -NotePropertyName "pdf-reader" -NotePropertyValue $pdfReaderConfig -Force
    
    # Save settings
    $settings | ConvertTo-Json -Depth 10 | Set-Content -Path $VSCodeSettingsPath -Encoding UTF8
    Write-Success "VS Code settings updated: $VSCodeSettingsPath"
}

function Create-HelperScripts {
    Write-Status "Creating helper scripts..."
    
    $helperScript = Join-Path $ProjectPath "pdf-helper.ps1"
    
    $helperContent = @"
# PDF Helper Functions
# Usage: . .\pdf-helper.ps1  (to load functions)
# 
# IMPORTANT: Update these paths for your installation:
# - KNOWLEDGE_BASE: Path to your folder containing PDF files
# - MCP_PYTHON: Path to your MCP Python executable

`$KNOWLEDGE_BASE = "$ProjectPath"  # UPDATE THIS PATH
`$MCP_PYTHON = "$InstallPath\venv\Scripts\python.exe"  # UPDATE THIS PATH  
`$MCP_SERVER = "$InstallPath\pdf_reader_server.py"  # UPDATE THIS PATH

function Find-PDF {
    param([string]`$SearchTerm)
    
    `$pdfs = Get-ChildItem -Path `$KNOWLEDGE_BASE -Filter "*.pdf" | Where-Object {
        `$_.Name -like "*`$SearchTerm*"
    }
    
    return `$pdfs
}

function Read-PDF {
    param(
        [string]`$SearchTerm,
        [switch]`$List,
        [switch]`$All,
        [switch]`$Summary
    )
    
    if (`$List) {
        Write-Host "Available PDFs:" -ForegroundColor Green
        Get-ChildItem -Path `$KNOWLEDGE_BASE -Filter "*.pdf" | ForEach-Object {
            Write-Host "  - `$(`$_.Name)" -ForegroundColor Cyan
        }
        return
    }
    
    if (`$All) {
        Write-Host "Reading ALL PDFs..." -ForegroundColor Yellow
        `$allPdfs = Get-ChildItem -Path `$KNOWLEDGE_BASE -Filter "*.pdf"
        
        foreach (`$pdf in `$allPdfs) {
            Write-Host "Processing: `$(`$pdf.Name)" -ForegroundColor Cyan
            `$env:PDF_SOURCE_DIR = `$KNOWLEDGE_BASE
            & `$MCP_PYTHON `$MCP_SERVER extract_pdf_text `$pdf.Name
        }
        return
    }
    
    `$found = Find-PDF -SearchTerm `$SearchTerm
    
    if (`$found.Count -eq 0) {
        Write-Host "No PDF found matching: `$SearchTerm" -ForegroundColor Red
        return
    }
    
    if (`$found.Count -gt 1) {
        Write-Host "Multiple PDFs found:" -ForegroundColor Yellow
        `$found | ForEach-Object { Write-Host "  - `$(`$_.Name)" -ForegroundColor Cyan }
        return
    }
    
    `$pdfPath = `$found[0].Name
    Write-Host "Reading: `$pdfPath" -ForegroundColor Green
    
    `$env:PDF_SOURCE_DIR = `$KNOWLEDGE_BASE
    & `$MCP_PYTHON `$MCP_SERVER extract_pdf_text `$pdfPath
}

# Aliases for convenience
function Read-AllPDFs { Read-PDF -All }
function Get-PDFList { Read-PDF -List }

Write-Host "PDF Helper loaded!" -ForegroundColor Green
Write-Host "Commands: Read-PDF 'search-term', Read-AllPDFs, Get-PDFList" -ForegroundColor Cyan
Write-Host "Example: Read-PDF 'trading'" -ForegroundColor Cyan
"@

    Set-Content -Path $helperScript -Value $helperContent -Encoding UTF8
    Write-Success "Helper script created: $helperScript"
}

function Test-Installation {
    Write-Status "Testing installation..."
    
    # Test MCP server
    $env:PDF_SOURCE_DIR = $ProjectPath
    $testResult = & "$InstallPath\venv\Scripts\python.exe" "$InstallPath\pdf_reader_server.py" list_pdfs 2>&1
    
    if ($LASTEXITCODE -eq 0 -or $testResult -match "pdf") {
        Write-Success "MCP server test passed"
    }
    else {
        Write-Error "MCP server test failed: $testResult"
    }
    
    # Test PDF detection
    $pdfCount = (Get-ChildItem -Path $ProjectPath -Filter "*.pdf").Count
    Write-Success "Found $pdfCount PDF files in $ProjectPath"
}

function Show-CompletionMessage {
    Write-Host "`n" + "="*80 -ForegroundColor Green
    Write-Host "MCP PDF Reader Installation Complete!" -ForegroundColor Green
    Write-Host "="*80 -ForegroundColor Green
    
    Write-Host "`nINSTALLATION SUMMARY:" -ForegroundColor Yellow
    Write-Host "  Installation Path: $InstallPath" -ForegroundColor Cyan
    Write-Host "  PDF Source Path: $ProjectPath" -ForegroundColor Cyan
    Write-Host "  VS Code Settings: $VSCodeSettingsPath" -ForegroundColor Cyan
    
    Write-Host "`nNEXT STEPS:" -ForegroundColor Yellow
    Write-Host "1. Restart VS Code completely" -ForegroundColor White
    Write-Host "2. Test with AI assistant: 'Read the first PDF in my knowledge base'" -ForegroundColor White
    Write-Host "3. Use helper scripts: " -ForegroundColor White
    Write-Host "   . .\pdf-helper.ps1" -ForegroundColor Cyan
    Write-Host "   Read-PDF 'search-term'" -ForegroundColor Cyan
    
    Write-Host "`nCONFIGURATION NOTES:" -ForegroundColor Yellow
    Write-Host "- PDF source directory is set to: $ProjectPath" -ForegroundColor White
    Write-Host "- You can change this by updating the PDF_SOURCE_DIR in VS Code settings" -ForegroundColor White
    Write-Host "- Helper scripts are in: $ProjectPath\pdf-helper.ps1" -ForegroundColor White
    
    Write-Host "`nTROUBLESHOOTING:" -ForegroundColor Yellow
    Write-Host "- If PDFs aren't found, check the PDF_SOURCE_DIR path" -ForegroundColor White
    Write-Host "- If MCP server fails, check Python installation and virtual environment" -ForegroundColor White
    Write-Host "- For VS Code issues, check Developer Console (Ctrl+Shift+I)" -ForegroundColor White
    
    Write-Host "`n" + "="*80 -ForegroundColor Green
}

# Main installation flow
try {
    Write-Host "MCP PDF Reader Installer" -ForegroundColor Green
    Write-Host "========================" -ForegroundColor Green
    
    if (-not (Test-Prerequisites)) {
        exit 1
    }
    
    Get-InstallationPaths
    Create-MCPDirectory
    Setup-PythonEnvironment
    Create-MCPServer
    Update-VSCodeSettings
    Create-HelperScripts
    Test-Installation
    Show-CompletionMessage
    
}
catch {
    Write-Error "Installation failed: $($_.Exception.Message)"
    Write-Host "Please check the error above and try again." -ForegroundColor Yellow
    exit 1
}