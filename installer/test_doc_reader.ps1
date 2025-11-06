# Test script for document reader MCP server
Write-Host "Testing Document Reader MCP Server..." -ForegroundColor Cyan

# Test 1: List documents
Write-Host "`n[Test 1] Listing documents in KnowledgeBase..." -ForegroundColor Yellow
$testRequest = @{
    jsonrpc = "2.0"
    method  = "tools/call"
    params  = @{
        name      = "list_documents"
        arguments = @{}
    }
    id      = 1
} | ConvertTo-Json -Depth 10

Write-Host "Request payload:`n$testRequest`n"

# Test 2: Extract PDF text
Write-Host "`n[Test 2] Extracting text from Bookmap User Guide (first 3 pages)..." -ForegroundColor Yellow
$testRequest2 = @{
    jsonrpc = "2.0"
    method  = "tools/call"
    params  = @{
        name      = "extract_document_text"
        arguments = @{
            filename   = "430196357-Bookmap-User-Guide-6-1.pdf"
            page_range = "1-3"
        }
    }
    id      = 2
} | ConvertTo-Json -Depth 10

Write-Host "Request payload:`n$testRequest2`n"

Write-Host "`nServer is running. Use the MCP client to send these requests." -ForegroundColor Green
Write-Host "Or restart VS Code to enable GitHub Copilot MCP integration." -ForegroundColor Green
