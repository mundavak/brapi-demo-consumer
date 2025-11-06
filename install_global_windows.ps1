# MCP PDF Reader - Global Installation Script for Windows 11
# Fixed version with proper escaping

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\Programs\MCPPDFReader",
    [string]$PDFSourceDir = "F:\TradingAgent\deaProjects\brapi-demo-consumer"
)

# Run as Administrator check
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script needs to run as Administrator to set up global access." -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "MCP PDF Reader - Global Installation for Windows 11" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Create installation directory
Write-Host "Creating installation directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Location $InstallDir

# Clone repository
Write-Host "Downloading MCP PDF Reader..." -ForegroundColor Yellow
if (Test-Path ".git") {
    git pull
}
else {
    git clone https://github.com/labeveryday/mcp_pdf_reader.git .
}

# Download main server file if missing
if (-not (Test-Path "pdf_reader_server.py")) {
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/labeveryday/mcp_pdf_reader/main/pdf_reader_server.py" -OutFile "pdf_reader_server.py"
}

# Create virtual environment
Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Install packages
Write-Host "Installing Python packages..." -ForegroundColor Yellow
& "$InstallDir\venv\Scripts\python.exe" -m pip install --upgrade pip
& "$InstallDir\venv\Scripts\pip.exe" install fastmcp PyMuPDF pytesseract Pillow

# Create the PDF processor module
Write-Host "Creating PDF processor module..." -ForegroundColor Yellow
@'
"""
PDF Processor Module for Global Access
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, List
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

# Configure Tesseract for Windows
tesseract_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\ProgramData\chocolatey\bin\tesseract.exe",
]

for path in tesseract_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        break

class PDFProcessor:
    def __init__(self, default_dir: str = r"F:\TradingAgent\deaProjects\brapi-demo-consumer"):
        self.default_dir = Path(default_dir) if default_dir else Path.cwd()
    
    def extract_text(self, pdf_path: Path, page_range: Optional[Dict] = None) -> Dict:
        """Extract text from PDF"""
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)
        
        doc = fitz.open(str(pdf_path))
        result = {
            "file": pdf_path.name,
            "path": str(pdf_path),
            "pages": [],
            "total_text": "",
            "word_count": 0
        }
        
        start = (page_range or {}).get("start", 1) - 1
        end = (page_range or {}).get("end", len(doc))
        
        for i in range(start, min(end, len(doc))):
            page = doc[i]
            text = page.get_text()
            result["pages"].append({
                "page": i + 1,
                "text": text,
                "words": len(text.split())
            })
            result["total_text"] += text + "\n"
            result["word_count"] += len(text.split())
        
        doc.close()
        return result
    
    def extract_with_ocr(self, pdf_path: Path, language: str = "eng") -> Dict:
        """Extract text using OCR"""
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)
            
        doc = fitz.open(str(pdf_path))
        result = {
            "file": pdf_path.name,
            "path": str(pdf_path),
            "ocr_pages": [],
            "total_text": "",
            "word_count": 0
        }
        
        for page_num, page in enumerate(doc, 1):
            # Get page as image
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Perform OCR
            try:
                text = pytesseract.image_to_string(img, lang=language)
                result["ocr_pages"].append({
                    "page": page_num,
                    "text": text,
                    "words": len(text.split())
                })
                result["total_text"] += text + "\n"
                result["word_count"] += len(text.split())
            except Exception as e:
                result["ocr_pages"].append({
                    "page": page_num,
                    "error": str(e)
                })
        
        doc.close()
        return result
    
    def analyze_structure(self, pdf_path: Path) -> Dict:
        """Analyze PDF structure"""
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)
            
        doc = fitz.open(str(pdf_path))
        result = {
            "file": pdf_path.name,
            "path": str(pdf_path),
            "page_count": len(doc),
            "metadata": doc.metadata,
            "pages_info": []
        }
        
        for page_num, page in enumerate(doc, 1):
            page_info = {
                "page": page_num,
                "width": page.rect.width,
                "height": page.rect.height,
                "text_length": len(page.get_text()),
                "image_count": len(page.get_images()),
                "links": len(page.get_links())
            }
            result["pages_info"].append(page_info)
        
        doc.close()
        return result
'@ | Out-File -FilePath "$InstallDir\pdf_processor.py" -Encoding UTF8

# Create the mcp-pdf.ps1 command script
Write-Host "Creating global command script..." -ForegroundColor Yellow
@'
param(
    [Parameter(Position=0)]
    [string]$Action = "help",
    [Parameter(Position=1)]
    [string]$Path = "",
    [string]$Output = "",
    [string]$Language = "eng"
)

$InstallDir = "$env:LOCALAPPDATA\Programs\MCPPDFReader"
$PythonExe = "$InstallDir\venv\Scripts\python.exe"
$DefaultPDFDir = "F:\TradingAgent\deaProjects\brapi-demo-consumer"

if ($Path -eq "") {
    if ($Action -in @("list", "batch")) {
        $Path = $DefaultPDFDir
    }
}

$script = @"
import sys
import os
import json
from pathlib import Path
sys.path.insert(0, '$InstallDir')

action = '$Action'
pdf_path = '$Path' if '$Path' else '.'
language = '$Language'
output = '$Output'

if action == 'help':
    print('''
MCP PDF Reader - Global Command
================================

Usage: mcp-pdf <action> [path] [options]

Actions:
  extract <file>  - Extract text from PDF
  ocr <file>      - Extract text using OCR
  analyze <file>  - Analyze PDF structure
  list [dir]      - List all PDFs in directory
  batch [dir]     - Process all PDFs in directory
  server          - Start MCP server
  gui             - Launch GUI interface
  help            - Show this help

Examples:
  mcp-pdf extract document.pdf
  mcp-pdf ocr scan.pdf
  mcp-pdf analyze report.pdf
  mcp-pdf list
  mcp-pdf batch .

Default PDF directory: F:\\TradingAgent\\deaProjects\\brapi-demo-consumer
    ''')

elif action == 'server':
    import subprocess
    subprocess.run([sys.executable, '$InstallDir\\pdf_reader_server.py'])

elif action in ['extract', 'ocr', 'analyze']:
    from pdf_processor import PDFProcessor
    processor = PDFProcessor()
    
    if action == 'extract':
        result = processor.extract_text(pdf_path)
    elif action == 'ocr':
        result = processor.extract_with_ocr(pdf_path, language)
    elif action == 'analyze':
        result = processor.analyze_structure(pdf_path)
    
    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f'Results saved to: {output}')
    else:
        print(json.dumps(result, indent=2))

elif action == 'list':
    from pathlib import Path
    pdf_dir = Path(pdf_path) if pdf_path else Path('.')
    pdfs = list(pdf_dir.glob('**/*.pdf'))
    print(f'Found {len(pdfs)} PDFs in {pdf_dir}:')
    for pdf in pdfs[:20]:
        print(f'  - {pdf.name}')
    if len(pdfs) > 20:
        print(f'  ... and {len(pdfs) - 20} more')

elif action == 'batch':
    from pathlib import Path
    from pdf_processor import PDFProcessor
    processor = PDFProcessor()
    pdf_dir = Path(pdf_path) if pdf_path else Path('.')
    pdfs = list(pdf_dir.glob('**/*.pdf'))
    print(f'Processing {len(pdfs)} PDFs...')
    for i, pdf in enumerate(pdfs, 1):
        print(f'{i}/{len(pdfs)}: {pdf.name}')
        try:
            result = processor.extract_text(pdf)
            print(f'  Extracted {result["word_count"]} words')
        except Exception as e:
            print(f'  Error: {e}')

elif action == 'gui':
    print('GUI feature coming soon!')
    print('For now, use the command line interface.')
"@

& $PythonExe -c $script
'@ | Out-File -FilePath "$InstallDir\mcp-pdf.ps1" -Encoding UTF8

# Create batch wrapper
Write-Host "Creating batch wrapper..." -ForegroundColor Yellow
@"
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$InstallDir\mcp-pdf.ps1" %*
"@ | Out-File -FilePath "$InstallDir\mcp-pdf.bat" -Encoding ASCII

# Add to PATH
Write-Host "Adding to system PATH..." -ForegroundColor Yellow
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$InstallDir", "Machine")
    Write-Host "Added to system PATH" -ForegroundColor Green
}
else {
    Write-Host "Already in PATH" -ForegroundColor Green
}

# Create desktop shortcut
Write-Host "Creating desktop shortcut..." -ForegroundColor Yellow
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\MCP PDF Reader.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoExit -ExecutionPolicy Bypass -Command `"&'$InstallDir\venv\Scripts\Activate.ps1'; Write-Host 'MCP PDF Reader Ready - Type: mcp-pdf help' -ForegroundColor Cyan`""
$Shortcut.WorkingDirectory = $PDFSourceDir
$Shortcut.IconLocation = "shell32.dll,1"
$Shortcut.Description = "MCP PDF Reader Environment"
$Shortcut.Save()

# Create Start Menu entry
$startMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\MCP PDF Reader"
New-Item -ItemType Directory -Force -Path $startMenuPath | Out-Null

$Shortcut = $WshShell.CreateShortcut("$startMenuPath\MCP PDF Reader.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoExit -ExecutionPolicy Bypass -Command `"&'$InstallDir\venv\Scripts\Activate.ps1'`""
$Shortcut.WorkingDirectory = $PDFSourceDir
$Shortcut.Save()

# Create context menu registry entries
Write-Host "Adding right-click context menu..." -ForegroundColor Yellow
$regPath = "Registry::HKEY_CLASSES_ROOT\.pdf\shell\MCPPDFReader"
New-Item -Path $regPath -Force | Out-Null
Set-ItemProperty -Path $regPath -Name "(Default)" -Value "Process with MCP PDF Reader"
Set-ItemProperty -Path $regPath -Name "Icon" -Value "shell32.dll,1"

New-Item -Path "$regPath\command" -Force | Out-Null
Set-ItemProperty -Path "$regPath\command" -Name "(Default)" -Value "`"powershell.exe`" -ExecutionPolicy Bypass -File `"$InstallDir\mcp-pdf.ps1`" extract `"%1`""

# Set environment variables
[Environment]::SetEnvironmentVariable("MCP_PDF_READER", $InstallDir, "User")
[Environment]::SetEnvironmentVariable("MCP_PDF_SOURCE", $PDFSourceDir, "User")

# Test the installation
Write-Host ""
Write-Host "Testing installation..." -ForegroundColor Yellow
& "$InstallDir\venv\Scripts\python.exe" -c "import pytesseract, fitz, PIL, fastmcp; print('All packages installed successfully!')"

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Installed to: $InstallDir" -ForegroundColor Cyan
Write-Host "Default PDF directory: $PDFSourceDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now use MCP PDF Reader from ANYWHERE:" -ForegroundColor Yellow
Write-Host ""
Write-Host "From Command Prompt or PowerShell:" -ForegroundColor White
Write-Host "  mcp-pdf help                    # Show help" -ForegroundColor Gray
Write-Host "  mcp-pdf extract document.pdf    # Extract text" -ForegroundColor Gray
Write-Host "  mcp-pdf ocr scan.pdf           # OCR extract" -ForegroundColor Gray
Write-Host "  mcp-pdf analyze report.pdf     # Analyze structure" -ForegroundColor Gray
Write-Host "  mcp-pdf list                   # List PDFs" -ForegroundColor Gray
Write-Host "  mcp-pdf batch                  # Process all PDFs" -ForegroundColor Gray
Write-Host ""
Write-Host "Right-click any PDF: 'Process with MCP PDF Reader'" -ForegroundColor White
Write-Host "Desktop shortcut: 'MCP PDF Reader'" -ForegroundColor White
Write-Host "Start Menu: Programs -> MCP PDF Reader" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: Restart terminals for PATH changes to take effect" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit"