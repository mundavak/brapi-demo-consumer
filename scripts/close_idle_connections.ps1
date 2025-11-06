# Close Idle PostgreSQL Connections
# Helps prevent connection pool exhaustion by terminating idle sessions

param(
    [int]$IdleMinutes = 5,
    [switch]$DryRun,
    [switch]$Verbose
)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "PostgreSQL Idle Connection Cleanup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# PostgreSQL connection details
$dbHost = "localhost"
$dbPort = 5432
$dbName = "trading_data"
$dbUser = "postgres"
$dbPassword = "X74Ot*BvtjgKuCBx"
$psqlPath = "C:\Program Files\PostgreSQL\17\bin\psql.exe"

# Build psql command to query idle connections
$query = @"
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    state_change,
    NOW() - state_change AS idle_duration,
    query
FROM pg_stat_activity
WHERE state = 'idle'
    AND NOW() - state_change > INTERVAL '$IdleMinutes minutes'
    AND pid <> pg_backend_pid()
    AND datname = '$dbName'
ORDER BY state_change;
"@

Write-Host "Checking for connections idle longer than $IdleMinutes minutes..." -ForegroundColor Yellow
Write-Host ""

# Query idle connections
$env:PGPASSWORD = $dbPassword
$idleConnections = & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -t -A -F "," -c $query 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to connect to PostgreSQL" -ForegroundColor Red
    Write-Host "   Check that PostgreSQL is running and credentials are correct" -ForegroundColor Red
    exit 1
}

if ([string]::IsNullOrWhiteSpace($idleConnections)) {
    Write-Host "✅ No idle connections found" -ForegroundColor Green
    Write-Host ""
    
    # Show current connection summary
    $summaryQuery = @"
SELECT 
    state,
    COUNT(*) as count
FROM pg_stat_activity
WHERE datname = '$dbName'
GROUP BY state
ORDER BY count DESC;
"@
    
    Write-Host "Current connection summary:" -ForegroundColor Cyan
    & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -c $summaryQuery 2>$null
    exit 0
}

# Parse idle connections
$connections = $idleConnections -split "`n" | Where-Object { $_ -ne "" }
$connectionCount = $connections.Count

Write-Host "Found $connectionCount idle connection(s):" -ForegroundColor Yellow
Write-Host ""

$pids = @()
foreach ($conn in $connections) {
    $fields = $conn -split ","
    if ($fields.Count -ge 8) {
        $pid = $fields[0]
        $user = $fields[1]
        $app = $fields[2]
        $clientAddr = $fields[3]
        $state = $fields[4]
        $idleDuration = $fields[6]
        
        $pids += $pid
        
        Write-Host "  PID: $pid" -ForegroundColor White
        Write-Host "    User: $user" -ForegroundColor Gray
        Write-Host "    Application: $app" -ForegroundColor Gray
        Write-Host "    Client: $clientAddr" -ForegroundColor Gray
        Write-Host "    Idle Duration: $idleDuration" -ForegroundColor Gray
        Write-Host ""
    }
}

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No connections will be terminated" -ForegroundColor Cyan
    Write-Host "   Remove -DryRun flag to actually close these connections" -ForegroundColor Cyan
    exit 0
}

# Confirm before terminating
Write-Host "⚠️  About to terminate $connectionCount idle connection(s)" -ForegroundColor Yellow
$confirmation = Read-Host "Continue? (y/N)"

if ($confirmation -ne "y" -and $confirmation -ne "Y") {
    Write-Host "Cancelled by user" -ForegroundColor Gray
    exit 0
}

Write-Host ""
Write-Host "Terminating idle connections..." -ForegroundColor Yellow

# Terminate each idle connection
$terminated = 0
foreach ($pid in $pids) {
    $terminateQuery = "SELECT pg_terminate_backend($pid);"
    $result = & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -t -A -c $terminateQuery 2>$null
    
    if ($LASTEXITCODE -eq 0 -and $result -match "t") {
        Write-Host "  ✓ Terminated PID $pid" -ForegroundColor Green
        $terminated++
    }
    else {
        Write-Host "  ✗ Failed to terminate PID $pid" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Terminated: $terminated / $connectionCount" -ForegroundColor $(if ($terminated -eq $connectionCount) { "Green" } else { "Yellow" })
Write-Host "================================================" -ForegroundColor Cyan

# Show updated connection summary
Write-Host ""
Write-Host "Current connection summary:" -ForegroundColor Cyan
$summaryQuery = @"
SELECT 
    state,
    COUNT(*) as count
FROM pg_stat_activity
WHERE datname = '$dbName'
GROUP BY state
ORDER BY count DESC;
"@

& $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -c $summaryQuery 2>$null

# Remove password from environment
Remove-Item Env:\PGPASSWORD
