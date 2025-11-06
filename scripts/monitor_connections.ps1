# Monitor PostgreSQL Connections
# Real-time monitoring of database connections with auto-refresh

param(
    [int]$RefreshSeconds = 5,
    [switch]$ShowQueries,
    [switch]$Once
)

function Show-ConnectionStatus {
    Clear-Host
    
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "PostgreSQL Connection Monitor" -ForegroundColor Cyan
    Write-Host "Database: trading_data" -ForegroundColor Cyan
    Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    
    # PostgreSQL connection details
    $dbHost = "localhost"
    $dbPort = 5432
    $dbName = "trading_data"
    $dbUser = "postgres"
    $dbPassword = "X74Ot*BvtjgKuCBx"
    $psqlPath = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
    $env:PGPASSWORD = $dbPassword
    
    # Query 1: Overall connection statistics
    $statsQuery = @"
SELECT 
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
    COUNT(*) FILTER (WHERE wait_event_type IS NOT NULL) as waiting
FROM pg_stat_activity
WHERE datname = '$dbName';
"@
    
    Write-Host "Connection Summary:" -ForegroundColor Yellow
    & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -c $statsQuery 2>$null
    Write-Host ""
    
    # Query 2: Connections by application
    $appQuery = @"
SELECT 
    COALESCE(application_name, 'Unknown') as application,
    state,
    COUNT(*) as count
FROM pg_stat_activity
WHERE datname = '$dbName'
GROUP BY application_name, state
ORDER BY count DESC, application;
"@
    
    Write-Host "Connections by Application:" -ForegroundColor Yellow
    & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -c $appQuery 2>$null
    Write-Host ""
    
    # Query 3: Long-running/idle connections
    $longRunningQuery = @"
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    EXTRACT(EPOCH FROM (NOW() - state_change))::INTEGER as idle_seconds,
    LEFT(query, 50) as query_preview
FROM pg_stat_activity
WHERE datname = '$dbName'
    AND pid <> pg_backend_pid()
    AND (
        state = 'active'
        OR (state = 'idle' AND NOW() - state_change > INTERVAL '2 minutes')
        OR state = 'idle in transaction'
    )
ORDER BY idle_seconds DESC
LIMIT 20;
"@
    
    Write-Host "Long-Running/Idle Connections (>2 min):" -ForegroundColor Yellow
    & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -c $longRunningQuery 2>$null
    Write-Host ""
    
    # Query 4: Database size and max connections
    $configQuery = @"
SELECT 
    current_setting('max_connections')::INTEGER as max_connections,
    (SELECT COUNT(*) FROM pg_stat_activity) as current_connections,
    pg_size_pretty(pg_database_size('$dbName')) as db_size;
"@
    
    Write-Host "Configuration:" -ForegroundColor Yellow
    & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -c $configQuery 2>$null
    
    # Show active queries if requested
    if ($ShowQueries) {
        Write-Host ""
        $activeQueriesQuery = @"
SELECT 
    pid,
    usename,
    application_name,
    state,
    query
FROM pg_stat_activity
WHERE datname = '$dbName'
    AND state = 'active'
    AND pid <> pg_backend_pid()
ORDER BY query_start DESC;
"@
        
        Write-Host "Active Queries:" -ForegroundColor Yellow
        & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -c $activeQueriesQuery 2>$null
    }
    
    # Remove password from environment
    Remove-Item Env:\PGPASSWORD
    
    if (-not $Once) {
        Write-Host ""
        Write-Host "Refreshing in $RefreshSeconds seconds... (Ctrl+C to stop)" -ForegroundColor Gray
    }
}

# Main loop
if ($Once) {
    Show-ConnectionStatus
}
else {
    while ($true) {
        Show-ConnectionStatus
        Start-Sleep -Seconds $RefreshSeconds
    }
}
