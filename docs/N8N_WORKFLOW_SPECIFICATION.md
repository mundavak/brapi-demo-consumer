# n8n Workflow Specifications for Trading Data Architecture

## Overview
This document specifies n8n workflows to orchestrate data flows between Redis (hot storage), TimescaleDB (cold storage), and external services. These workflows automate data synchronization, monitoring, and alerting.

**Note:** You will need to create an n8n account and implement these workflows after completing the Java component deployment.

---

## Workflow 1: Redis to TimescaleDB Sync Monitor

**Purpose:** Monitor Redis data freshness and trigger manual sync if automatic batch processing fails

**Trigger:** Schedule (every 5 minutes)

**Nodes:**

1. **Schedule Trigger**
   - Cron: `*/5 * * * *` (every 5 minutes)

2. **Redis Client - Check Queue Depth**
   - Connect to: `localhost:6379`
   - Commands:
     ```
     LLEN batch:mbo
     LLEN batch:ohlc
     LLEN batch:stops
     LLEN batch:absorption
     ```
   - Store results in variables

3. **IF Node - Queue Too Deep?**
   - Condition: Any queue > 1000 items
   - True → Alert
   - False → Continue

4. **Alert Webhook** (if queue deep)
   - Method: POST
   - URL: Your monitoring service
   - Body:
     ```json
     {
       "alert": "Redis batch queue depth exceeded threshold",
       "queues": "{{$json.queues}}",
       "timestamp": "{{$now}}"
     }
     ```

5. **HTTP Request - Trigger Manual Sync**
   - Method: POST
   - URL: `http://localhost:8080/api/force-sync`
   - Headers: `Content-Type: application/json`

---

## Workflow 2: CBDR Window Notifications

**Purpose:** Send notifications when entering/exiting CBDR windows for trading alerts

**Trigger:** Webhook + Schedule

**Nodes:**

1. **Schedule Trigger**
   - Cron: `*/1 * * * *` (every minute)

2. **Execute Command - Check CBDR Status**
   - Command: `redis-cli HGETALL cbdr:MNQ:PM`
   - Parse response to check status

3. **IF Node - Window Active?**
   - Check if status == "ACTIVE"
   - True → Notify
   - False → Skip

4. **Redis Client - Get Window Data**
   - Get absorption events:
     ```
     ZREVRANGE absorption:MNQ:PM 0 9
     ```
   - Get market bias:
     ```
     HGETALL bias:MNQ
     ```

5. **Transform Data Node**
   - Parse JSON from Redis
   - Format for dashboard
   - Calculate summary statistics

6. **HTTP Request - Update Dashboard**
   - Method: POST
   - URL: `http://localhost:3000/api/cbdr-update`
   - Body:
     ```json
     {
       "symbol": "MNQ",
       "window": "PM",
       "bias": "{{$json.bias}}",
       "events": "{{$json.events}}",
       "timestamp": "{{$now}}"
     }
     ```

7. **Discord/Slack Webhook** (optional)
   - Send CBDR window alerts to trading channel

---

## Workflow 3: Symbol Selection Manager

**Purpose:** Manage active symbol configuration and propagate changes to all consumers

**Trigger:** Webhook (manual trigger from dashboard)

**Nodes:**

1. **Webhook Trigger**
   - Path: `/api/symbol/update`
   - Method: POST
   - Expected Body:
     ```json
     {
       "symbol": "BTC",
       "action": "activate"
     }
     ```

2. **Read Symbol Config**
   - File: `F:/TradingAgent/Dashboard/symbol_config.json`
   - Parse JSON

3. **Validate Symbol**
   - Check if symbol exists in config
   - Check if already active
   - Validate action (activate/deactivate)

4. **Update JSON Config**
   - Modify `isActive` field
   - Write back to file

5. **Redis Client - Update Active Symbols**
   - If activate:
     ```
     SADD symbols:active {{$json.symbol}}
     HSET symbol:{{$json.symbol}}:config active true
     ```
   - If deactivate:
     ```
     SREM symbols:active {{$json.symbol}}
     HSET symbol:{{$json.symbol}}:config active false
     ```

6. **TimescaleDB - Create Session**
   - Execute SQL:
     ```sql
     INSERT INTO trading_sessions (session_id, symbol, session_type, start_time, status)
     VALUES (
       '{{$json.symbol}}_{{$now.format("YYYYMMDD")}}_MANUAL',
       '{{$json.symbol}}',
       'MANUAL',
       NOW(),
       'ACTIVE'
     );
     ```

7. **Publish to Redis**
   - Publish notification:
     ```
     PUBLISH signals:system "SYMBOL_CHANGE:{{$json.symbol}}:{{$json.action}}"
     ```

8. **Response Node**
   - Return success/failure status

---

## Workflow 4: Daily HTF Analysis Export

**Purpose:** Export higher timeframe analysis data from TimescaleDB for offline analysis

**Trigger:** Schedule (daily at 00:05 EST)

**Nodes:**

1. **Schedule Trigger**
   - Cron: `5 0 * * *` (00:05 daily)
   - Timezone: America/New_York

2. **TimescaleDB Query - Get Daily Summary**
   - SQL:
     ```sql
     SELECT * FROM daily_statistics
     WHERE day = CURRENT_DATE - INTERVAL '1 day';
     ```

3. **TimescaleDB Query - Get HTF Candles**
   - SQL:
     ```sql
     SELECT * FROM ohlc_1h_aggregate
     WHERE hour >= CURRENT_DATE - INTERVAL '1 day'
     AND hour < CURRENT_DATE
     ORDER BY hour, symbol;
     ```

4. **Transform to CSV**
   - Convert JSON to CSV format
   - Include headers

5. **Write File**
   - Path: `F:/TradingAgent/Dashboard/exports/htf_analysis_{{$now.format("YYYYMMDD")}}.csv`

6. **Compress File** (optional)
   - Create ZIP archive
   - Keep last 30 days

7. **Upload to Cloud** (optional)
   - S3/Google Drive upload
   - For backup and remote analysis

---

## Workflow 5: Performance Monitoring & Alerts

**Purpose:** Monitor system performance and send alerts for degradation

**Trigger:** Schedule (every 30 seconds)

**Nodes:**

1. **Schedule Trigger**
   - Cron: `*/30 * * * * *` (every 30 seconds)

2. **Redis Client - Get Stats**
   - Commands:
     ```
     INFO stats
     INFO memory
     DBSIZE
     ```

3. **Parse Redis Stats**
   - Extract:
     - Total commands/sec
     - Used memory
     - Connected clients
     - Key count

4. **TimescaleDB - Check Connections**
   - SQL:
     ```sql
     SELECT count(*) FROM pg_stat_activity
     WHERE datname = 'trading_data';
     ```

5. **Check Log Files**
   - Read: `F:/Databases/Logs/trading_system_summary.log`
   - Count ERROR lines in last minute

6. **Calculate Metrics**
   - Redis ops/sec
   - DB connection pool usage
   - Error rate
   - Memory usage %

7. **IF Node - Any Threshold Exceeded?**
   - Memory > 80%
   - Error rate > 5/min
   - DB connections > 15

8. **Alert Webhook** (if threshold exceeded)
   - Method: POST
   - Body:
     ```json
     {
       "alert_type": "performance_degradation",
       "metrics": "{{$json.metrics}}",
       "timestamp": "{{$now}}"
     }
     ```

9. **Store Metrics in InfluxDB/Prometheus** (optional)
   - For long-term monitoring dashboard

---

## Workflow 6: Data Integrity Check

**Purpose:** Verify Redis and TimescaleDB are in sync

**Trigger:** Schedule (hourly)

**Nodes:**

1. **Schedule Trigger**
   - Cron: `0 * * * *` (hourly)

2. **Redis Client - Count Recent Events**
   - Count events in last hour:
     ```
     ZCOUNT mbo:MNQ:session {{$now - 3600000}} {{$now}}
     ZCOUNT stops:MNQ:session {{$now - 3600000}} {{$now}}
     ```

3. **TimescaleDB - Count Recent Events**
   - SQL:
     ```sql
     SELECT
       (SELECT COUNT(*) FROM mbo_data WHERE timestamp > NOW() - INTERVAL '1 hour') as mbo_count,
       (SELECT COUNT(*) FROM stops_icebergs WHERE timestamp > NOW() - INTERVAL '1 hour') as stops_count,
       (SELECT COUNT(*) FROM absorption_events WHERE timestamp > NOW() - INTERVAL '1 hour') as absorption_count;
     ```

4. **Compare Counts**
   - Calculate difference %
   - Acceptable threshold: 5%

5. **IF Node - Data Mismatch?**
   - If difference > 5%
   - True → Alert
   - False → Log success

6. **Alert Webhook** (if mismatch)
   - Notify of potential data sync issue

7. **Log to File**
   - Append to: `F:/Databases/Logs/integrity_checks.log`

---

## Workflow 7: Auto-Restart Failed Consumers

**Purpose:** Detect and restart crashed consumer JARs

**Trigger:** Schedule (every 2 minutes)

**Nodes:**

1. **Schedule Trigger**
   - Cron: `*/2 * * * *`

2. **Check Process Status**
   - Execute PowerShell:
     ```powershell
     Get-Process -Name "java" -ErrorAction SilentlyContinue | 
     Where-Object {$_.CommandLine -like "*Demo-Consumer*"}
     ```

3. **Parse Running Consumers**
   - Check for each JAR:
     - StopsIcebergsConsumer
     - OhlcCandleConsumer
     - AbsorptionConsumer

4. **Check Last Update Time in Redis**
   - For each consumer, check:
     ```
     GET consumer:{{name}}:last_heartbeat
     ```
   - If > 5 minutes old → consider crashed

5. **IF Node - Consumer Down?**
   - If process missing OR heartbeat old
   - True → Restart
   - False → Continue

6. **Execute Command - Restart Bookmap** (if consumer down)
   - PowerShell:
     ```powershell
     Start-Process "C:\Program Files\Bookmap\Bookmap.exe" -ArgumentList "-reloadAddons"
     ```

7. **Alert Webhook**
   - Notify of restart action

8. **Wait & Verify**
   - Wait 30 seconds
   - Check Redis heartbeat again

---

## Implementation Guide

### Prerequisites

1. **n8n Installation**
   ```bash
   npm install -g n8n
   # or Docker:
   docker run -it --rm --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n
   ```

2. **Configure Credentials in n8n**
   - Redis: `localhost:6379` (no password by default)
   - PostgreSQL: `localhost:5432/trading_data` (postgres user)
   - Webhooks: Configure endpoints

3. **Enable Workflows**
   - Import JSON workflow definitions
   - Activate each workflow
   - Test with manual triggers

### Workflow Execution Order

1. Start with Workflow 5 (Performance Monitoring) - basic health checks
2. Enable Workflow 1 (Sync Monitor) - ensure data flows
3. Enable Workflow 6 (Data Integrity) - verify sync quality
4. Enable Workflow 2 (CBDR Notifications) - trading alerts
5. Enable Workflow 3 (Symbol Selection) - operational control
6. Enable Workflow 7 (Auto-Restart) - reliability
7. Enable Workflow 4 (HTF Export) - analysis pipelines

### Monitoring Dashboard

Create n8n dashboard to visualize:
- Workflow execution counts
- Success/failure rates
- Alert history
- System metrics

---

## Advanced Features (Future Enhancement)

1. **Machine Learning Integration**
   - Export data to Python ML models
   - Ingest predictions back to Redis

2. **Multi-Exchange Support**
   - Add workflows for BTC from different exchanges
   - Aggregate data across sources

3. **Backtesting Pipeline**
   - Export TimescaleDB data for backtesting
   - Automate strategy testing

4. **Real-Time Strategy Execution**
   - Connect to broker APIs
   - Automate order placement based on signals

---

## Cost & Performance Considerations

- **n8n Cloud:** $20/month (recommended for reliability)
- **Self-Hosted:** Free (requires maintenance)
- **Workflow Executions:** Optimize schedules to stay within limits
- **Database Queries:** Use indexes and time-based partitioning
- **Redis Memory:** Monitor with Workflow 5

---

## Next Steps for User

1. ✅ Complete Java component deployment
2. ✅ Verify Redis and TimescaleDB are operational
3. ⏳ Create n8n account (n8n.io or self-host)
4. ⏳ Import workflow JSON files (to be created)
5. ⏳ Configure credentials in n8n
6. ⏳ Test each workflow individually
7. ⏳ Enable production workflows
8. ⏳ Monitor via n8n dashboard

---

## Support & Resources

- n8n Documentation: https://docs.n8n.io/
- Community Forum: https://community.n8n.io/
- Workflow Templates: https://n8n.io/workflows/

**Workflow JSON files will be created after you set up your n8n instance.**
