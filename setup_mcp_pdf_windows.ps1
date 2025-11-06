# MCP PDF Reader - Global Installation Script for Windows 11
# This script makes the PDF reader accessible from anywhere on your system

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
Write-Host "📁 Creating installation directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Location $InstallDir

# Clone repository
Write-Host "📥 Downloading MCP PDF Reader..." -ForegroundColor Yellow
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
Write-Host "🐍 Creating Python virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Install packages
Write-Host "📦 Installing Python packages..." -ForegroundColor Yellow
& "$InstallDir\venv\Scripts\python.exe" -m pip install --upgrade pip
& "$InstallDir\venv\Scripts\pip.exe" install fastmcp PyMuPDF pytesseract Pillow

# Create global command script
Write-Host "🔧 Creating global command scripts..." -ForegroundColor Yellow

# Create PowerShell global command
$psCommand = @"
<#
.SYNOPSIS
    MCP PDF Reader - Global Command
.DESCRIPTION
    Process PDFs from anywhere on your system
.PARAMETER Action
    The action to perform: extract, ocr, analyze, server
.PARAMETER Path
    Path to the PDF file or directory
.PARAMETER Output
    Output directory for results
#>
param(
    [Parameter(Position=0)]
    [ValidateSet('extract', 'ocr', 'analyze', 'server', 'gui', 'help')]
    [string]`$Action = 'help',
    
    [Parameter(Position=1)]
    [string]`$Path = '$PDFSourceDir',
    
    [string]`$Output = '.',
    [int]`$StartPage = 1,
    [int]`$EndPage = -1,
    [string]`$Language = 'eng'
)

`$env:PYTHONPATH = "$InstallDir"
`$pythonExe = "$InstallDir\venv\Scripts\python.exe"

# Import the module
`$script = @'
import sys
import os
import json
from pathlib import Path
sys.path.insert(0, "$InstallDir")

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'help'
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else '$PDFSourceDir'
    
    if action == 'help':
        print('''
MCP PDF Reader - Global Command
================================

Usage: mcp-pdf <action> [path] [options]

Actions:
  extract <file>  - Extract text from PDF
  ocr <file>      - Extract text using OCR
  analyze <file>  - Analyze PDF structure
  server          - Start MCP server
  gui             - Launch GUI interface
  help            - Show this help

Examples:
  mcp-pdf extract document.pdf
  mcp-pdf ocr "C:\\Documents\\scan.pdf"
  mcp-pdf analyze .  # Analyze all PDFs in current directory
  mcp-pdf server     # Start the MCP server

Default PDF directory: $PDFSourceDir
        ''')
        return
    
    if action == 'server':
        import subprocess
        subprocess.run([sys.executable, "$InstallDir\\pdf_reader_server.py"])
    
    elif action in ['extract', 'ocr', 'analyze']:
        from pdf_processor import PDFProcessor
        processor = PDFProcessor()
        
        pdf_path = Path(pdf_path)
        if pdf_path.is_dir():
            pdfs = list(pdf_path.glob("**/*.pdf"))
            print(f"Found {len(pdfs)} PDFs in {pdf_path}")
            for pdf in pdfs:
                print(f"Processing: {pdf.name}")
                if action == 'extract':
                    result = processor.extract_text(pdf)
                elif action == 'ocr':
                    result = processor.extract_with_ocr(pdf)
                elif action == 'analyze':
                    result = processor.analyze_structure(pdf)
                print(f"  Result: {result.get('word_count', 0)} words")
        else:
            if action == 'extract':
                result = processor.extract_text(pdf_path)
            elif action == 'ocr':
                result = processor.extract_with_ocr(pdf_path)
            elif action == 'analyze':
                result = processor.analyze_structure(pdf_path)
            
            print(json.dumps(result, indent=2))
    
    elif action == 'gui':
        from pdf_gui import launch_gui
        launch_gui()

if __name__ == "__main__":
    main()
'@

& `$pythonExe -c `$script `$Action `$Path
"@

$psCommandPath = "$InstallDir\mcp-pdf.ps1"
Set-Content -Path $psCommandPath -Value $psCommand

# Create batch file wrapper
$batchCommand = @"
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$InstallDir\mcp-pdf.ps1" %*
"@

$batchPath = "$InstallDir\mcp-pdf.bat"
Set-Content -Path $batchPath -Value $batchCommand

# Create Python processor module
Write-Host "📝 Creating PDF processor module..." -ForegroundColor Yellow

$processorCode = @'
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
'@

Set-Content -Path "$InstallDir\pdf_processor.py" -Value $processorCode

# Create GUI module (optional)
Write-Host "🎨 Creating GUI module..." -ForegroundColor Yellow

$guiCode = @'
"""
Simple GUI for PDF Reader
"""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path
import json
import threading
from pdf_processor import PDFProcessor

class PDFReaderGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MCP PDF Reader")
        self.root.geometry("900x600")
        
        self.processor = PDFProcessor()
        self.setup_ui()
    
    def setup_ui(self):
        # File selection frame
        file_frame = ttk.Frame(self.root, padding="10")
        file_frame.pack(fill=tk.X)
        
        ttk.Label(file_frame, text="PDF File:").pack(side=tk.LEFT)
        self.file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT)
        
        # Action buttons
        action_frame = ttk.Frame(self.root, padding="10")
        action_frame.pack(fill=tk.X)
        
        ttk.Button(action_frame, text="Extract Text", command=self.extract_text).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="OCR Extract", command=self.ocr_extract).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Analyze", command=self.analyze).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Clear", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        
        # Output area
        output_frame = ttk.Frame(self.root, padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(output_frame, text="Output:").pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status, relief=tk.SUNKEN).pack(fill=tk.X)
    
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filename:
            self.file_path.set(filename)
    
    def extract_text(self):
        self.process_pdf("extract")
    
    def ocr_extract(self):
        self.process_pdf("ocr")
    
    def analyze(self):
        self.process_pdf("analyze")
    
    def process_pdf(self, action):
        pdf_path = self.file_path.get()
        if not pdf_path:
            messagebox.showwarning("No File", "Please select a PDF file first")
            return
        
        self.status.set(f"Processing {action}...")
        self.output_text.delete(1.0, tk.END)
        
        def process():
            try:
                if action == "extract":
                    result = self.processor.extract_text(Path(pdf_path))
                elif action == "ocr":
                    result = self.processor.extract_with_ocr(Path(pdf_path))
                elif action == "analyze":
                    result = self.processor.analyze_structure(Path(pdf_path))
                
                self.output_text.insert(tk.END, json.dumps(result, indent=2))
                self.status.set(f"Completed: {result.get('word_count', 'N/A')} words")
            except Exception as e:
                self.output_text.insert(tk.END, f"Error: {str(e)}")
                self.status.set("Error occurred")
        
        threading.Thread(target=process, daemon=True).start()
    
    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
        self.status.set("Ready")
    
    def run(self):
        self.root.mainloop()

def launch_gui():
    app = PDFReaderGUI()
    app.run()

if __name__ == "__main__":
    launch_gui()
'@

Set-Content -Path "$InstallDir\pdf_gui.py" -Value $guiCode

# Add to PATH
Write-Host "🔗 Adding to system PATH..." -ForegroundColor Yellow

$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$InstallDir", "Machine")
    Write-Host "✅ Added to system PATH" -ForegroundColor Green
}
else {
    Write-Host "✅ Already in PATH" -ForegroundColor Green
}

# Create Windows Terminal profile
Write-Host "🖥️ Creating Windows Terminal profile..." -ForegroundColor Yellow

$terminalProfile = @{
    "name"              = "MCP PDF Reader"
    "commandline"       = "powershell.exe -NoExit -Command `"& '$InstallDir\venv\Scripts\Activate.ps1'; Set-Location '$PDFSourceDir'`""
    "startingDirectory" = $PDFSourceDir
    "icon"              = "📄"
    "colorScheme"       = "Campbell"
}

$terminalProfilePath = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"
if (Test-Path $terminalProfilePath) {
    Write-Host "   Add this profile to Windows Terminal settings:" -ForegroundColor Yellow
    Write-Host ($terminalProfile | ConvertTo-Json) -ForegroundColor Cyan
}

# Create desktop shortcut
Write-Host "🔗 Creating desktop shortcut..." -ForegroundColor Yellow

$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\MCP PDF Reader.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoExit -ExecutionPolicy Bypass -Command `"& '$InstallDir\venv\Scripts\Activate.ps1'; Write-Host 'MCP PDF Reader Ready - Type: mcp-pdf help' -ForegroundColor Cyan`""
$Shortcut.WorkingDirectory = $PDFSourceDir
$Shortcut.IconLocation = "shell32.dll,1"
$Shortcut.Description = "MCP PDF Reader Environment"
$Shortcut.Save()

# Create Start Menu entry
$startMenuPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\MCP PDF Reader"
New-Item -ItemType Directory -Force -Path $startMenuPath | Out-Null

$Shortcut = $WshShell.CreateShortcut("$startMenuPath\MCP PDF Reader.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoExit -ExecutionPolicy Bypass -Command `"& '$InstallDir\venv\Scripts\Activate.ps1'`""
$Shortcut.WorkingDirectory = $PDFSourceDir
$Shortcut.Save()

$Shortcut = $WshShell.CreateShortcut("$startMenuPath\MCP PDF GUI.lnk")
$Shortcut.TargetPath = "$InstallDir\venv\Scripts\pythonw.exe"
$Shortcut.Arguments = "$InstallDir\pdf_gui.py"
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Save()

# Create context menu registry entries
Write-Host "📋 Adding right-click context menu..." -ForegroundColor Yellow

$regPath = "Registry::HKEY_CLASSES_ROOT\.pdf\shell\MCPPDFReader"
New-Item -Path $regPath -Force | Out-Null
Set-ItemProperty -Path $regPath -Name "(Default)" -Value "Process with MCP PDF Reader"
Set-ItemProperty -Path $regPath -Name "Icon" -Value "shell32.dll,1"

New-Item -Path "$regPath\command" -Force | Out-Null
Set-ItemProperty -Path "$regPath\command" -Name "(Default)" -Value "`"powershell.exe`" -ExecutionPolicy Bypass -File `"$InstallDir\mcp-pdf.ps1`" extract `"%1`""

# Create environment variable
[Environment]::SetEnvironmentVariable("MCP_PDF_READER", $InstallDir, "User")
[Environment]::SetEnvironmentVariable("MCP_PDF_SOURCE", $PDFSourceDir, "User")

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "✅ Global Installation Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Installed to: $InstallDir" -ForegroundColor Cyan
Write-Host "📂 Default PDF directory: $PDFSourceDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎯 You can now use MCP PDF Reader from ANYWHERE:" -ForegroundColor Yellow
Write-Host ""
Write-Host "From Command Prompt or PowerShell:" -ForegroundColor White
Write-Host "  mcp-pdf help                    # Show help" -ForegroundColor Gray
Write-Host "  mcp-pdf extract document.pdf    # Extract text from PDF" -ForegroundColor Gray
Write-Host "  mcp-pdf ocr scan.pdf           # OCR extract from PDF" -ForegroundColor Gray
Write-Host "  mcp-pdf analyze .              # Analyze all PDFs in current directory" -ForegroundColor Gray
Write-Host "  mcp-pdf gui                    # Launch GUI interface" -ForegroundColor Gray
Write-Host "  mcp-pdf server                 # Start MCP server" -ForegroundColor Gray
Write-Host ""
Write-Host "Right-click any PDF file:" -ForegroundColor White
Write-Host "  Select 'Process with MCP PDF Reader'" -ForegroundColor Gray
Write-Host ""
Write-Host "Desktop shortcut:" -ForegroundColor White
Write-Host "  Double-click 'MCP PDF Reader' on desktop" -ForegroundColor Gray
Write-Host ""
Write-Host "Start Menu:" -ForegroundColor White
Write-Host "  Programs → MCP PDF Reader" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️ IMPORTANT: Restart any open terminals for PATH changes to take effect" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
"@