# MCP PDF Reader - Path Fix Script
# Fixes the path escaping issue in the installed mcp-pdf.ps1

$InstallDir = "$env:LOCALAPPDATA\Programs\MCPPDFReader"

Write-Host "Fixing MCP PDF Reader path issues..." -ForegroundColor Yellow

# Create fixed mcp-pdf.ps1 with properly escaped paths
$FixedScript = @'
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

# Use forward slashes for Python paths
$InstallDirPython = $InstallDir -replace '\\', '/'
$PathPython = $Path -replace '\\', '/'

$script = @"
import sys
import os
import json
from pathlib import Path

# Use forward slashes for Python
sys.path.insert(0, r'$InstallDirPython')

action = '$Action'
pdf_path = r'$PathPython' if '$PathPython' else '.'
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
    server_path = r'$InstallDirPython/pdf_reader_server.py'
    subprocess.run([sys.executable, server_path])

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
'@

# Write the fixed script
Set-Content -Path "$InstallDir\mcp-pdf.ps1" -Value $FixedScript -Encoding UTF8

Write-Host "Fixed mcp-pdf.ps1 script!" -ForegroundColor Green

# Also create a simpler direct Python launcher
$PythonLauncher = @"
#!/usr/bin/env python
import sys
import os
import json
from pathlib import Path

# Add installation directory to path
install_dir = r"$($InstallDir -replace '\\', '/')"
sys.path.insert(0, install_dir)

def main():
    if len(sys.argv) < 2:
        action = 'help'
    else:
        action = sys.argv[1]
    
    if action == 'help':
        print('''
MCP PDF Reader - Commands
==========================

Usage: mcp-pdf <action> [file/directory]

Actions:
  extract <file>  - Extract text from PDF
  ocr <file>      - Extract text using OCR  
  analyze <file>  - Analyze PDF structure
  list [dir]      - List PDFs in directory
  batch [dir]     - Process all PDFs
  server          - Start MCP server
  help            - Show this help

Examples:
  mcp-pdf extract document.pdf
  mcp-pdf list
  mcp-pdf batch F:\\TradingAgent\\deaProjects\\brapi-demo-consumer
        ''')
        return
    
    # Import processor
    from pdf_processor import PDFProcessor
    processor = PDFProcessor()
    
    if action == 'extract' and len(sys.argv) > 2:
        pdf_path = sys.argv[2]
        result = processor.extract_text(pdf_path)
        print(json.dumps(result, indent=2))
    
    elif action == 'list':
        directory = sys.argv[2] if len(sys.argv) > 2 else '.'
        pdfs = list(Path(directory).glob('**/*.pdf'))
        print(f'Found {len(pdfs)} PDFs:')
        for pdf in pdfs[:20]:
            print(f'  - {pdf.name}')
    
    elif action == 'batch':
        directory = sys.argv[2] if len(sys.argv) > 2 else '.'
        pdfs = list(Path(directory).glob('**/*.pdf'))
        for pdf in pdfs:
            print(f'Processing: {pdf.name}')
            try:
                result = processor.extract_text(str(pdf))
                print(f'  Extracted {result["word_count"]} words')
            except Exception as e:
                print(f'  Error: {e}')

if __name__ == '__main__':
    main()
"@

Set-Content -Path "$InstallDir\mcp-pdf-launcher.py" -Value $PythonLauncher -Encoding UTF8

# Create a new batch file that uses the Python launcher
@"
@echo off
"$InstallDir\venv\Scripts\python.exe" "$InstallDir\mcp-pdf-launcher.py" %*
"@ | Out-File -FilePath "$InstallDir\mcp-pdf-direct.bat" -Encoding ASCII

Write-Host "Created alternative launcher: mcp-pdf-direct.bat" -ForegroundColor Green

Write-Host ""
Write-Host "================================================" -ForegroundColor Green  
Write-Host "Fix Applied Successfully!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "You can now use:" -ForegroundColor Yellow
Write-Host "  mcp-pdf help              # Should work now!" -ForegroundColor White
Write-Host "  mcp-pdf-direct help       # Alternative command" -ForegroundColor White
Write-Host ""
Write-Host "Try it now:" -ForegroundColor Cyan
