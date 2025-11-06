# Stop Redis Stack and TimescaleDB Docker containers

Write-Host "=== Stopping Bookmap Trading Stack ===" -ForegroundColor Cyan

$projectRoot = "F:\TradingAgent\deaProjects\brapi-demo-consumer"
Set-Location $projectRoot

Write-Host ""
Write-Host "Stopping containers..." -ForegroundColor Yellow
docker-compose stop

Write-Host ""
Write-Host "✓ Containers stopped" -ForegroundColor Green
Write-Host ""
Write-Host "To start again: .\scripts\start_redis_stack_docker.ps1" -ForegroundColor Gray
Write-Host "To remove completely: docker-compose down -v" -ForegroundColor Gray
Write-Host ""
