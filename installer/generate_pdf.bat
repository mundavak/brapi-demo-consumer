@echo off
echo Generating Installation Guide PDF...
echo ===================================

REM Try to generate PDF using Python script
python generate_pdf.py

REM If that fails, suggest alternatives
if %errorlevel% neq 0 (
    echo.
    echo Alternative PDF generation methods:
    echo.
    echo 1. Using pandoc (if installed):
    echo    pandoc MCP_PDF_Reader_Installation_Guide.md -o MCP_PDF_Reader_Installation_Guide.pdf --css=style.css
    echo.
    echo 2. Using VS Code:
    echo    - Open MCP_PDF_Reader_Installation_Guide.md in VS Code
    echo    - Install "Markdown PDF" extension
    echo    - Right-click and select "Markdown PDF: Export (pdf)"
    echo.
    echo 3. Online converter:
    echo    - Go to https://www.markdowntopdf.com/
    echo    - Upload the .md file
    echo    - Download the generated PDF
    echo.
)

pause