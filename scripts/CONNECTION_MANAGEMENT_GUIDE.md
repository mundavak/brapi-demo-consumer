# PostgreSQL Connection Management Scripts

## Overview
Two PowerShell scripts for monitoring and managing PostgreSQL connections to prevent connection pool exhaustion.

## Scripts

### 1. Monitor Connections (`monitor_connections.ps1`)
Real-time monitoring of database connections with detailed statistics.

**Usage:**
```powershell
# One-time check
.\scripts\monitor_connections.ps1 -Once

# Continuous monitoring (refreshes every 5 seconds)
.\scripts\monitor_connections.ps1

# Custom refresh rate
.\scripts\monitor_connections.ps1 -RefreshSeconds 10

# Show active queries
.\scripts\monitor_connections.ps1 -Once -ShowQueries
```

**Output:**
- Connection summary (total, active, idle, waiting)
- Connections by application name and state
- Long-running/idle connections (>2 minutes)
- Database configuration (max_connections, current usage, db size)
- Optional: Active queries with full SQL

### 2. Close Idle Connections (`close_idle_connections.ps1`)
Terminates idle connections to free up connection pool slots.

**Usage:**
```powershell
# Dry run - see what would be closed (default: 5+ minutes idle)
.\scripts\close_idle_connections.ps1 -DryRun

# Actually close idle connections (5+ minutes)
.\scripts\close_idle_connections.ps1

# Custom idle threshold (2+ minutes)
.\scripts\close_idle_connections.ps1 -IdleMinutes 2

# Close with confirmation prompt
.\scripts\close_idle_connections.ps1 -IdleMinutes 3
```

**Safety Features:**
- Dry run mode by default shows what would be closed
- Never terminates the script's own connection
- Confirmation prompt before terminating connections
- Detailed logging of each terminated connection

## Database Configuration

**Current Settings:**
- Database: `trading_data`
- Host: `localhost`
- Port: `5432`
- User: `postgres`
- Max Connections: `200` (increased from 100)

## Connection Pool Settings (HikariCP)

**From `database_config.properties`:**
- Pool size: `20`
- Min idle: `5`
- Max lifetime: `1800000` ms (30 minutes)
- Connection timeout: `30000` ms (30 seconds)

## Common Issues & Solutions

### Issue 1: "Too many clients already"
**Symptoms:** PostgreSQL rejects new connections when pool is exhausted
**Solutions:**
1. Run `.\scripts\close_idle_connections.ps1 -IdleMinutes 2` to free idle connections
2. Increase `max_connections` in `postgresql.conf` (already set to 200)
3. Reduce `timescaledb.pool.size` in `database_config.properties` if too aggressive

### Issue 2: Connection leaks
**Symptoms:** Connections remain idle indefinitely
**Root Causes:**
- HikariCP `max.lifetime` too high (currently 30 min)
- Application not properly closing connections
- Long-running transactions not committing

**Solutions:**
1. Monitor regularly: `.\scripts\monitor_connections.ps1`
2. Set up scheduled task to close idle connections every 5 minutes
3. Reduce HikariCP `max.lifetime` to 10-15 minutes

### Issue 3: Performance degradation
**Symptoms:** Slow queries, connection timeouts
**Check:**
1. `.\scripts\monitor_connections.ps1 -Once -ShowQueries` - see blocking queries
2. Look for connections in "idle in transaction" state (locks held)
3. Check for long-running active queries (>30 seconds)

## Automated Cleanup (Optional)

Create a Windows Scheduled Task to run every 5 minutes:

```powershell
# Create scheduled task (run as Administrator)
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File F:\TradingAgent\deaProjects\brapi-demo-consumer\scripts\close_idle_connections.ps1 -IdleMinutes 5"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -Action $action -Trigger $trigger `
    -TaskName "PostgreSQL-CleanupIdleConnections" `
    -Description "Closes idle PostgreSQL connections every 5 minutes"
```

## Monitoring Best Practices

1. **Before Trading Session:**
   - Run `monitor_connections.ps1 -Once` to check baseline
   - Close any stale connections from previous sessions

2. **During Active Trading:**
   - Monitor every 5-10 minutes if experiencing issues
   - Watch for sudden spikes in idle connections

3. **After Trading Session:**
   - Close all idle connections: `close_idle_connections.ps1 -IdleMinutes 1`
   - Check database size growth: monitor output shows `db_size`

## Troubleshooting

**Script fails with "psql not found":**
- Install PostgreSQL client tools
- Or update `$psqlPath` in scripts to match your installation

**"Failed to connect to PostgreSQL":**
- Check PostgreSQL service is running: `Get-Service postgresql*`
- Verify password in scripts matches `database_config.properties`
- Test connection: `& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h localhost -U postgres -d trading_data -c "SELECT 1;"`

**No idle connections found but pool still exhausted:**
- All connections may be in "active" state
- Check for long-running queries: `monitor_connections.ps1 -ShowQueries`
- May need to increase `max_connections` further or reduce `pool.size`
