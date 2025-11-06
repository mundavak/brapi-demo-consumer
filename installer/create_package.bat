@echo off
echo Creating MCP PDF Reader Installer Package...
echo ===========================================

REM Create distribution directory
if exist "dist" rmdir /s /q dist
mkdir dist

echo Copying installer files...

REM Copy main installer files
copy "install.bat" "dist\"
copy "Install-MCP-PDFReader.ps1" "dist\"
copy "pdf_reader_server.py" "dist\"
copy "README.md" "dist\"
copy "QUICK_START.md" "dist\"
copy "MANUAL_INSTALL.md" "dist\"

REM Copy documentation
copy "MCP_PDF_Reader_Installation_Guide.md" "dist\"
if exist "MCP_PDF_Reader_Installation_Guide.pdf" copy "MCP_PDF_Reader_Installation_Guide.pdf" "dist\"

REM Copy optional files
copy "style.css" "dist\"
copy "generate_pdf.py" "dist\"
copy "generate_pdf.bat" "dist\"

REM Create a simple template (without my specific paths)
echo Creating generic VS Code settings template...
echo { > "dist\vscode-settings-template.json"
echo   "github.copilot.chat.mcpServers": { >> "dist\vscode-settings-template.json"
echo     "pdf-reader": { >> "dist\vscode-settings-template.json"
echo       "command": "PATH_TO_INSTALLATION\\venv\\Scripts\\python.exe", >> "dist\vscode-settings-template.json"
echo       "args": [ >> "dist\vscode-settings-template.json"
echo         "PATH_TO_INSTALLATION\\pdf_reader_server.py" >> "dist\vscode-settings-template.json"
echo       ], >> "dist\vscode-settings-template.json"
echo       "env": { >> "dist\vscode-settings-template.json"
echo         "PDF_SOURCE_DIR": "PATH_TO_YOUR_PDFS", >> "dist\vscode-settings-template.json"
echo         "PYTHONPATH": "PATH_TO_INSTALLATION" >> "dist\vscode-settings-template.json"
echo       } >> "dist\vscode-settings-template.json"
echo     } >> "dist\vscode-settings-template.json"
echo   } >> "dist\vscode-settings-template.json"
echo } >> "dist\vscode-settings-template.json"

REM Generate PDF if possible
echo Attempting to generate PDF guide...
call generate_pdf.bat > nul 2>&1
if exist "MCP_PDF_Reader_Installation_Guide.pdf" (
    copy "MCP_PDF_Reader_Installation_Guide.pdf" "dist\"
    echo   ✓ PDF guide included
) else (
    echo   ! PDF guide not generated - manual creation required
)

echo.
echo Package created in 'dist' folder with these files:
echo   ✓ install.bat                              (Quick installer)
echo   ✓ QUICK_START.md                           (Start here!)
echo   ✓ Install-MCP-PDFReader.ps1               (PowerShell installer)
echo   ✓ pdf_reader_server.py                    (MCP server script)
echo   ✓ README.md                               (Package overview)
echo   ✓ MANUAL_INSTALL.md                       (Manual setup guide)
echo   ✓ MCP_PDF_Reader_Installation_Guide.md    (Complete guide)
echo   ✓ vscode-settings-template.json           (Settings template)

if exist "dist\MCP_PDF_Reader_Installation_Guide.pdf" (
    echo   ✓ MCP_PDF_Reader_Installation_Guide.pdf   (PDF guide)
)

echo.
echo Ready to share! Your friend should:
echo 1. Download the entire 'dist' folder
echo 2. Double-click 'install.bat' to run the installer
echo 3. Follow the prompts to specify their paths
echo 4. Restart VS Code after installation

pause