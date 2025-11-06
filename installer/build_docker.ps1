# Build the Docker image
Write-Host "Building MCP Document Reader Docker image..." -ForegroundColor Cyan
docker build -t mcp-doc-reader:latest -f installer/Dockerfile installer/

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Image built successfully!" -ForegroundColor Green
    
    # Test the image
    Write-Host "`nTesting the Docker container..." -ForegroundColor Yellow
    docker run --rm `
        -v "F:/TradingAgent/deaProjects/brapi-demo-consumer/KnowledgeBase:/knowledge-base:ro" `
        -e PDF_SOURCE_DIR=/knowledge-base `
        mcp-doc-reader:latest python -c "import fitz, docx; print('✅ All dependencies working')"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Container test passed!" -ForegroundColor Green
        Write-Host "`nTo run the MCP server:" -ForegroundColor Cyan
        Write-Host "  docker-compose -f docker-compose.mcp.yml up -d" -ForegroundColor White
        Write-Host "`nTo view logs:" -ForegroundColor Cyan
        Write-Host "  docker logs -f mcp-doc-reader" -ForegroundColor White
        Write-Host "`nTo stop:" -ForegroundColor Cyan
        Write-Host "  docker-compose -f docker-compose.mcp.yml down" -ForegroundColor White
    }
    else {
        Write-Host "❌ Container test failed" -ForegroundColor Red
    }
}
else {
    Write-Host "❌ Build failed" -ForegroundColor Red
}
