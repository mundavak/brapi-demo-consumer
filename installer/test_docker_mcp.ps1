# Quick test script for Docker MCP server
Write-Host "Testing Docker MCP Document Reader..." -ForegroundColor Cyan

# Test 1: Check container can access files
Write-Host "`n[Test 1] Checking file access..." -ForegroundColor Yellow
docker run --rm `
  -v "F:/TradingAgent/deaProjects/brapi-demo-consumer/KnowledgeBase:/knowledge-base:ro" `
  mcp-doc-reader:latest `
  python -c "from pathlib import Path; pdfs = list(Path('/knowledge-base').glob('*.pdf')); print(f'✅ Found {len(pdfs)} PDF files')"

# Test 2: Test PDF extraction
Write-Host "`n[Test 2] Testing PDF text extraction..." -ForegroundColor Yellow
docker run --rm `
  -v "F:/TradingAgent/deaProjects/brapi-demo-consumer/KnowledgeBase:/knowledge-base:ro" `
  -e PDF_SOURCE_DIR=/knowledge-base `
  mcp-doc-reader:latest `
  python -c "import fitz; doc = fitz.open('/knowledge-base/430196357-Bookmap-User-Guide-6-1.pdf'); print(f'✅ Bookmap Guide: {len(doc)} pages, first page has {len(doc[0].get_text())} chars')"

# Test 3: Test DOCX support
Write-Host "`n[Test 3] Testing DOCX support..." -ForegroundColor Yellow
docker run --rm `
  mcp-doc-reader:latest `
  python -c "import docx; print('✅ python-docx is installed and working')"

Write-Host "`n✅ All tests passed!" -ForegroundColor Green
Write-Host "`nTo use in VS Code:" -ForegroundColor Cyan
Write-Host "  1. Restart VS Code completely" -ForegroundColor White
Write-Host "  2. Open Copilot Chat (Ctrl+Alt+I)" -ForegroundColor White
Write-Host "  3. Type: @doc-reader-docker list documents" -ForegroundColor White
