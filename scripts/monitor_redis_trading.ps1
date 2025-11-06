# Redis Data Monitor for Stops & Icebergs and Absorption Consumers

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Redis Data Monitor - Trading Consumers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Redis connection test
Write-Host "Testing Redis connection..." -ForegroundColor Yellow
try {
    $redisInfo = docker exec bookmap-bookmap-redis-stack redis-cli ping
    if ($redisInfo -eq "PONG") {
        Write-Host "✓ Redis is running" -ForegroundColor Green
    }
}
catch {
    Write-Host "✗ Redis connection failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Scanning for active sessions and data..." -ForegroundColor Yellow
Write-Host ""

# Function to parse Redis hash and display nicely
function Show-RedisHash {
    param(
        [string]$Key,
        [string]$Title
    )
    
    Write-Host "[$Title] Key: $Key" -ForegroundColor Cyan
    $hashData = docker exec bookmap-redis-stack redis-cli HGETALL $Key
    
    if ($hashData) {
        for ($i = 0; $i -lt $hashData.Count; $i += 2) {
            $field = $hashData[$i]
            $value = $hashData[$i + 1]
            Write-Host "  $field = $value" -ForegroundColor White
        }
    }
    else {
        Write-Host "  (empty)" -ForegroundColor Gray
    }
    Write-Host ""
}

# Function to get list items
function Show-RedisList {
    param(
        [string]$Key,
        [string]$Title,
        [int]$Count = 5
    )
    
    Write-Host "[$Title] Key: $Key" -ForegroundColor Cyan
    $listLen = docker exec bookmap-redis-stack redis-cli LLEN $Key
    Write-Host "  List Length: $listLen" -ForegroundColor Yellow
    
    if ([int]$listLen -gt 0) {
        $items = docker exec bookmap-redis-stack redis-cli LRANGE $Key 0 ($Count - 1)
        Write-Host "  First $Count items:" -ForegroundColor White
        foreach ($item in $items) {
            Write-Host "    - $item" -ForegroundColor Gray
        }
    }
    Write-Host ""
}

# 1. Check for active sessions
Write-Host "=== ACTIVE SESSIONS ===" -ForegroundColor Magenta
$sessions = docker exec bookmap-redis-stack redis-cli KEYS "session:*"
if ($sessions) {
    foreach ($session in $sessions) {
        Show-RedisHash $session "Session Info"
    }
}
else {
    Write-Host "No active sessions found" -ForegroundColor Yellow
}

# 2. Check Stops & Icebergs data
Write-Host "=== STOPS & ICEBERGS DATA ===" -ForegroundColor Magenta

# Check for stop/iceberg events by pattern
$stopKeys = docker exec bookmap-redis-stack redis-cli KEYS "stop:*"
$icebergKeys = docker exec bookmap-redis-stack redis-cli KEYS "iceberg:*"

Write-Host "Stop event keys: $($stopKeys.Count)" -ForegroundColor Yellow
Write-Host "Iceberg event keys: $($icebergKeys.Count)" -ForegroundColor Yellow
Write-Host ""

if ($stopKeys) {
    Write-Host "Sample Stop Events:" -ForegroundColor Cyan
    for ($i = 0; $i -lt [Math]::Min(3, $stopKeys.Count); $i++) {
        Show-RedisHash $stopKeys[$i] "Stop Event"
    }
}

if ($icebergKeys) {
    Write-Host "Sample Iceberg Events:" -ForegroundColor Cyan
    for ($i = 0; $i -lt [Math]::Min(3, $icebergKeys.Count); $i++) {
        Show-RedisHash $icebergKeys[$i] "Iceberg Event"
    }
}

# Check for any stop/iceberg lists or sorted sets
$stopLists = docker exec bookmap-redis-stack redis-cli KEYS "stops:*"
$icebergLists = docker exec bookmap-redis-stack redis-cli KEYS "icebergs:*"

if ($stopLists) {
    foreach ($list in $stopLists) {
        Show-RedisList $list "Stops List"
    }
}

if ($icebergLists) {
    foreach ($list in $icebergLists) {
        Show-RedisList $list "Icebergs List"
    }
}

# 3. Check Absorption data
Write-Host "=== ABSORPTION DATA ===" -ForegroundColor Magenta

$absorptionKeys = docker exec bookmap-redis-stack redis-cli KEYS "absorption:*"
Write-Host "Absorption event keys: $($absorptionKeys.Count)" -ForegroundColor Yellow
Write-Host ""

if ($absorptionKeys) {
    Write-Host "Sample Absorption Events:" -ForegroundColor Cyan
    for ($i = 0; $i -lt [Math]::Min(3, $absorptionKeys.Count); $i++) {
        Show-RedisHash $absorptionKeys[$i] "Absorption Event"
    }
}

# Check for absorption lists
$absorptionLists = docker exec bookmap-redis-stack redis-cli KEYS "absorptions:*"
if ($absorptionLists) {
    foreach ($list in $absorptionLists) {
        Show-RedisList $list "Absorptions List"
    }
}

# 4. Check MBO data (for comparison - we know this works)
Write-Host "=== MBO DATA (Reference) ===" -ForegroundColor Magenta
$mboKeys = docker exec bookmap-redis-stack redis-cli KEYS "mbo:*"
Write-Host "MBO event keys: $($mboKeys.Count)" -ForegroundColor Yellow
if ($mboKeys.Count -gt 0) {
    Write-Host "Sample MBO Event:" -ForegroundColor Cyan
    Show-RedisHash $mboKeys[0] "MBO Event"
}

# 5. Check all keys to see what's actually being stored
Write-Host "=== ALL REDIS KEYS SUMMARY ===" -ForegroundColor Magenta
$allKeys = docker exec bookmap-redis-stack redis-cli KEYS "*"
$keyGroups = $allKeys | Group-Object { ($_ -split ":")[0] }

Write-Host "Key prefixes found:" -ForegroundColor Yellow
foreach ($group in $keyGroups | Sort-Object Count -Descending) {
    Write-Host "  $($group.Name): $($group.Count) keys" -ForegroundColor White
}
Write-Host ""

# 6. Monitor Redis INFO for memory and stats
Write-Host "=== REDIS SERVER INFO ===" -ForegroundColor Magenta
$redisStats = docker exec bookmap-redis-stack redis-cli INFO stats
$memoryInfo = docker exec bookmap-redis-stack redis-cli INFO memory

# Parse and display key stats
$statsLines = $redisStats -split "`n"
foreach ($line in $statsLines) {
    if ($line -match "total_commands_processed|total_connections_received|instantaneous_ops_per_sec") {
        Write-Host "  $line" -ForegroundColor White
    }
}

$memoryLines = $memoryInfo -split "`n"
foreach ($line in $memoryLines) {
    if ($line -match "used_memory_human|used_memory_peak_human") {
        Write-Host "  $line" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Monitoring complete." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
