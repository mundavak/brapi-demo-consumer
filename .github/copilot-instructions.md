F# Bookmap Broadcasting API Demo Consumer - AI Coding Guide

## AI Memory Location

**Persistent Document Storage:** `H:\AiMemory\`

- **Documents:** `H:\AiMemory\documents\` - 59 extracted text files from KnowledgeBase (PDFs, DOCX, MD)
- **Index:** `H:\AiMemory\index\latest_index.json` - Metadata for all extracted documents
- **Contents:** All 60 KnowledgeBase documents extracted with OCR support
  - 46 PDFs (including ICT trading guides, Bookmap manuals, order flow analysis)
  - 8 DOCX files (Bookmap courses, ICT mentorship notes)
  - 6 MD files (API documentation, trading guides)
- **Usage:** Read directly from `H:\AiMemory\documents\` for instant access to any document without re-extraction
- **Search:** Use PowerShell `Select-String` or query the JSON index for semantic search

## Project Overview

This is a **Bookmap plugin/addon** project that demonstrates how to consume and provide trading data using Bookmap's Broadcasting API (BrAPI). The project contains multiple addons showing different consumer/provider patterns for real-time trading data analysis.

**Critical Understanding**: This is NOT a standalone application - it's a **plugin that runs inside Bookmap's classloader**. Many API classes (like `Layer1ApiProvider`, `InstrumentInfo`) won't compile standalone but work at runtime when loaded by Bookmap.

**Trading Safety**: Always test in simulation first. Bookmap's simulation has unrealistically low latency (local machine). Use server-side demo accounts before considering live trading. Both your code and the API may contain bugs.

## Architecture Components

### Three Main Addon Types

1. **Demo Consumer** (`DemoConsumer.java`) - Full-featured consumer connecting to multiple providers (Absorption, Sweep, Stops & Icebergs, Market Pulse)
2. **Simple Demo Consumer** (`SimpleDemoConsumer.java`) - Basic consumer connecting only to Absorption Indicator
3. **Simple Demo Provider** (`SimpleDemoProvider.java`) - Provider broadcasting moving average events

### Module Types & Capabilities

**Attached Modules** (`@Layer1Attachable`) - Most common type:

- Don't require forwarding messages (more efficient than Injected)
- Can't intercept downstream events (like user sending orders)
- See effects of downstream events as upstream responses
- Use for most consumers/indicators

**Injected Modules** (`@Layer1Injectable`) - Advanced use:

- Must forward all upstream/downstream events
- Can alter downstream events (reject orders, add confirmations)
- Control exact timing of event propagation
- Slight performance cost
- Extend `Layer1ApiRelay` or `Layer1ApiInjectorRelay`

**Data Editor Modules** (`@Layer1UpstreamDataEditor`) - Specialized:

- Rewrite upstream events below data structure layer
- Create synthetic instruments, filter data
- Must restore initial state on unload
- Cannot use most extensions

### Key Addon Structure Pattern

```java
@Layer1Attachable
@Layer1StrategyName("Your Addon Name")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class YourAddon implements
        Layer1ApiFinishable,           // Cleanup lifecycle
        Layer1ApiAdminAdapter,          // Admin messages
        Layer1ApiInstrumentAdapter,     // Instrument events
        Layer1CustomPanelsGetter {      // GUI panels
```

### Broadcasting API Core Pattern

All addons follow this initialization:

```java
// For consumers
BroadcasterConsumer broadcaster = BroadcastFactory.getBroadcasterConsumer(provider, ADDON_NAME, this.getClass());
broadcaster.start();
broadcaster.connectToProvider(providerName, connectionListener);

// For providers
BroadcasterProvider broadcaster = BroadcastFactory.getBroadcasterProvider(provider, ADDON_NAME, this.getClass());
broadcaster.start();
```

### Data Storage Architecture

The project uses **dual-storage** for real-time trading data:

- **Redis** (`RedisManager.java`) - Hot storage for real-time access with configurable TTLs
- **TimescaleDB** (`TimescaleDBManager.java`) - Cold storage for historical analysis
- Both managers use **singleton pattern** and batch processing via `BlockingQueue`

Example: `StopsIcebergsConsumer` and `OhlcCandleConsumer` write to both simultaneously.

### Bookmap API Layers & Data Flow

**Data flows in BOTH directions through a chain of layers:**

- **Upstream**: Market data flows up from providers → adapters → modules → GUI
- **Downstream**: User actions flow down from GUI → modules → providers
- Events are timestamped at adapter level; delays "slow down time" rather than changing timestamps
- **Synchronization Rule**: NEVER synchronize upstream/downstream streams (use `Layer1ApiInjectorRelay#inject` for cross-stream communication)

**Three ways to access data:**

1. **Real-time events** - Via listener interfaces (fastest, streaming)
2. **Data Structure Interface** - Query aggregated data with `Layer1ApiDataInterfaceRequestMessage` (fast for historical ranges)
3. **Custom Generators** - Store computed values as points for efficient retrieval (`Layer1ApiUserMessageAddStrategyUpdateGenerator`)

## Critical Build Requirements

### The Bookmap API JAR Problem

**This project will NOT compile without the Bookmap API JAR.** This is expected and documented in `COMPILATION_FIX.md`.

**Why this happens:**

- Bookmap API is `compileOnly` dependency (not included in final JAR)
- At runtime, Bookmap's classloader provides these classes (parent-first classloader)
- This is standard practice for plugin development
- Your module loads into a custom child classloader

**Solution**: Copy Bookmap's API JAR from your installation:

```cmd
copy "C:\Program Files\Bookmap\lib\api-core-*.jar" "mavenLib\com\bookmap\api\api-core\7.5.0.4\"
```

**Classloader & Compatibility:**

- Parent-first: Bookmap classes override yours if conflicts exist
- Can ship libraries via "fat jar" but watch for conflicts with Bookmap's `lib/` folder
- `@Layer1ApiVersion` annotation ensures compatibility when breaking changes occur
- Bookmap adjusts compatibility layer for older API versions automatically

### Build Dependencies

- **Java 11+** (set `JAVA_HOME` before building)
- Bookmap API: `api-core-7.5.0.4` (compileOnly - provided by Bookmap at runtime)
- Broadcasting API: `broadcasting-api-3.0.0.18` (included in JAR)
- Provider modules in `providers/modules/*.jar` (dynamic classpath)
- Redis client: `jedis-5.1.0`
- PostgreSQL driver: `postgresql-42.7.1`
- Connection pooling: `HikariCP-5.1.0`

### Build Workflow

```powershell
# Standard build
.\gradlew.bat clean build

# Automated build + copy to Bookmap
.\build_jars.bat

# Manual copy task
.\gradlew.bat copyJars
```

**Important**: `build.gradle` has `copyJars` task that auto-copies to `F:/Bookmap/Python/build/` after build.

## Provider Integration Pattern

### Supported Providers

Located in `providers/modules/` as pre-compiled JARs:

- Absorption Indicator (v4.52)
- Stops & Icebergs On-Chart
- Sweep Indicator
- Market Pulse

### Adding New Provider Support

1. Add provider JAR to `providers/modules/`
2. Create `ProviderValueHandler` in `src/main/java/com/bookmap/demo/consumer/providers/value/`
3. Create `InstrumentsController` in `src/main/java/com/bookmap/demo/consumer/providers/instruments/`
4. Register in connection manager

Example: `AbsorptionAndSweepsValueHandler.java` shows event casting pattern:

```java
EventInterface event = CastUtilities.castObject(o, TradeEvent.class);
```

### Generator & Filter Pattern

Providers have generators (one per instrument/alias) with:

- Settings (cannot be changed by consumer)
- Filters (must be applied to match provider visualization)

```java
List<GeneratorInfo> info = broadcaster.getGeneratorsInfo(PROVIDER_NAME);
// Subscribe with UpdateFilterListener and UpdateSettingsListener
```

## Session Management

All consumers use `SessionManager.getInstance().generateSessionId(symbol)` for tracking:

- Format: `{symbol}_{yyyyMMdd_HHmmss}_{UUID}`
- Used as keys in both Redis and TimescaleDB
- Enables session-based data retrieval

## Common Patterns

### Lifecycle Management

```java
@Override
public void onUserMessage(Object data) {
    if (data instanceof UserMessageLayersChainCreatedTargeted message) {
        if (message.targetClass == getClass()) {
            isWorking.set(true);
            broadcaster.start();
        }
    }
}

@Override
public void finish() {
    broadcaster.finish();
    // Cleanup resources
}
```

### Concurrent Data Structures

Use `ConcurrentHashMap` for instrument tracking:

```java
private final Map<String, String> activeSymbols = new ConcurrentHashMap<>();
private final Map<String, Map<Double, PriceLevelTracker>> bidTrackers = new ConcurrentHashMap<>();
```

### Batch Processing Pattern

```java
private final BlockingQueue<Event> batchQueue = new LinkedBlockingQueue<>(5000);
private final ScheduledExecutorService batchProcessor = Executors.newSingleThreadScheduledExecutor();

// Schedule batch processing every N seconds
batchProcessor.scheduleAtFixedRate(this::processBatch, 5, 5, TimeUnit.SECONDS);
```

## Testing & Deployment

### Installation

1. Build JAR: `gradlew.bat clean build`
2. Copy from `build/libs/` to Bookmap addons folder (usually `C:\Users\<User>\Bookmap\AddOns\`)
3. Restart Bookmap (doesn't cache classes - full reload on restart)
4. Enable in **Settings → Manage Addons** (or **Settings → API plugins configuration**)

### Fast Development Cycle (No JAR Rebuild)

Create `bm-strategy-package-fs-root.jar` (empty file) in your build output folder:

```powershell
# Example: Strategies\build\classes\java\main
New-Item -Path "build\classes\java\main\bm-strategy-package-fs-root.jar" -ItemType File
```

- Load this file into Bookmap (Settings → API plugins configuration → Add)
- Bookmap loads classes from folder instead of JAR file
- Restart Bookmap after code changes (or hot-swap with debugger attached)
- File can be deleted after first load

### IDE Debugging Setup

**Run Bookmap from IDE** (IntelliJ/Eclipse):

1. Set JDK version matching Bookmap (check `C:\Program Files\Bookmap\jre\bin\java --version`)
2. Add to classpath: `C:\Program Files\Bookmap\Bookmap.jar`
3. Working directory: `C:\Bookmap` (or custom config location)
4. Main class: `velox.ib.Main`
5. For Java 16+, add `--add-opens` JVM args:

```
--add-opens=java.base/java.lang=ALL-UNNAMED
--add-opens=java.base/java.io=ALL-UNNAMED
--add-opens=java.desktop/java.awt=ALL-UNNAMED
(see BookmapAPIREADME.md for full list)
```

6. **Critical**: Ensure `compileOnly` dependencies DON'T appear in classpath (causes NoSuchMethodError)

### Verification (see `VERIFICATION_GUIDE.md`)

- Check Bookmap logs for startup messages
- Add addon to chart via right-click → Indicators
- Monitor output files (configured in manager classes)
- Provider must be enabled on same instrument

### Common Issues

- Missing Bookmap API JAR → compilation fails (expected during dev)
- Provider not active → consumer receives no events
- Wrong Java version → build fails
- Redis/TimescaleDB not running → storage fails silently (check logs)
- Black areas on heatmap (Windows IDE) → Fix Java scaling in `java.exe` properties → Compatibility → Override high DPI

## MCP Document Reader Setup

**Integrated PDF/DOCX Reader** for AI assistants via Model Context Protocol (MCP):

### Quick Start

1. **Server is auto-configured** in `.vscode/settings.json`:

```json
{
  "github.copilot.chat.mcpServers": {
    "doc-reader": {
      "command": "python",
      "args": ["installer/pdf_reader_server.py"],
      "env": {
        "PDF_SOURCE_DIR": "F:\\TradingAgent\\deaProjects\\brapi-demo-consumer\\KnowledgeBase"
      }
    }
  }
}
```

2. **Restart VS Code** to enable MCP integration

3. **Query documents naturally** in Copilot Chat:

```
@doc-reader list available documents
@doc-reader extract text from "Bookmap-User-Guide-6-1.pdf" pages 1-10
@doc-reader read "ICT-Mentorship-Month-1-Notes.pdf"
```

### Supported File Types

- **PDF** - Full text extraction with page range support (46 PDFs in KnowledgeBase)
- **DOCX** - Paragraph-level extraction
- **TXT/MD** - Full content reading

### Docker Option (Recommended for Production)

```powershell
# Build image
.\installer\build_docker.ps1

# Run with Docker Compose
docker-compose -f docker-compose.mcp.yml up -d

# Or use in VS Code with @doc-reader-docker
```

**Benefits**: Isolated environment, consistent dependencies, read-only document access

### Key Documents (78+ PDFs in KnowledgeBase)

- `430196357-Bookmap-User-Guide-6-1.pdf` - Complete Bookmap API documentation
- `443878056-ICT-Mentorship-Month-1-Notes.pdf` - ICT trading concepts (Expansion, Retracement, Reversal)
- `435949428-The-Ultimate-Guide-To-Order-Flow-Trading.pdf` - Order flow analysis patterns
- `Stops and Icebergs_ How to Detect Hidden Orders Using MBO Data.pdf` - Iceberg detection algorithms
- `Cracking the Spoofing Code_Inside the World of Market Manipulation.pdf` - Spoofing techniques
- `TimescaleDB_Starter_Guide.pdf` - Database setup for cold storage
- `how-to-manage-a-redis-database.pdf` - Redis configuration

### PowerShell Helpers (legacy - use MCP instead)

```powershell
. .\scripts\pdf-helper.ps1  # Load helpers
Read-Bookmap               # Bookmap User Guide
Read-ICT                   # ICT Mentorship notes
Read-OrderFlow             # Order flow trading guide
```

## File Organization

- `src/main/java/com/bookmap/demo/consumer/` - Consumer addons
- `src/main/java/com/bookmap/demo/simple/` - Simple examples (consumer + provider)
- `src/main/java/com/bookmap/demo/consumer/database/` - Storage managers
- `src/main/java/com/bookmap/demo/consumer/providers/` - Provider-specific handlers
- `KnowledgeBase/` - API documentation and Javadocs
- `mavenLib/` - Local Maven repository (must contain Bookmap API JAR)
- `providers/modules/` - Provider JARs for classpath

## Simplified API vs Core API

**When to use Simplified API** (`velox.api.layer1.simplified`):

- Getting started with Bookmap development
- Building indicators that process events in time order
- Need price/time coordinate-based drawing (lines, icons)
- Don't need to intercept downstream events

**Simplified API Features:**

- Auto-handles snapshot + live updates
- Three operational modes (live-only, live+history with/without notification)
- Storage options: in-memory (200k points, modifiable) or on-disk (unlimited, immutable)
- Listener interfaces: `TradeDataListener`, `DepthDataListener`, `BboListener`, `IntervalListener`, etc.

**When to use Core API**:

- Need full control over event processing
- Intercept/modify downstream events (orders, user actions)
- Create data editors or synthetic instruments
- Maximum performance requirements
- Access to all extension systems (generators, indicators, screen painters)

**Core API Complexity:**

- Manual snapshot/update handling
- Explicit lifecycle management (`UserMessageLayersChainCreatedTargeted`)
- Must implement proper forwarding in injected modules
- Requires understanding of layered architecture

## Performance Considerations

**Critical**: Code runs in main event stack after adapter layer:

- Slow processing "slows down time" (timeline moves slower)
- Bookmap queues events and catches up during bursts
- Generators execute in main stack after historical data processed
- `OnlineValueCalculator` runs in main stack after catch-up

**Optimization strategies:**

- Use batch processing with `BlockingQueue` (see `StopsIcebergsConsumer`)
- Offload heavy computation to separate threads
- Use `ScheduledExecutorService` for periodic tasks
- Query Data Structure Interface for ranges (faster than iterating events)

## Key Documentation

- `README.md` - BrAPI consumer/provider workflow
- `COMPILATION_FIX.md` - How to resolve missing Bookmap API JAR
- `VERIFICATION_GUIDE.md` - Testing and deployment steps
- `KnowledgeBase/BookmapAPIREADME.md` - Core Bookmap API reference (342 lines - comprehensive)
- `KnowledgeBase/bm-simplified-api-wrapper-javadoc/` - Javadoc for Simplified API interfaces
- `KnowledgeBase/PythonAPI_README.md` - Python API reference (different from Java API)

## KnowledgeBase PDF Resources (78 files)

**Critical Technical Documentation:**

- `430196357-Bookmap-User-Guide-6-1.pdf` - Complete Bookmap user guide with API integration
- `373723507-Bookmap-User-Guide-5-0.pdf` - Earlier version for compatibility reference
- `Bookmap API _ Bookmap Knowledge Base.pdf` - Official API documentation
- `java-developers-guide.pdf` - Java development patterns and best practices
- `TimescaleDB_Starter_Guide.pdf` - Database setup for cold storage
- `how-to-manage-a-redis-database.pdf` - Redis configuration for hot storage
- `postgresql-16-A4.pdf` - PostgreSQL reference for TimescaleDB

**Trading Concepts & Order Flow (Relevant to Consumer Logic):**

- `443878056-ICT-Mentorship-Month-1-Notes.pdf` - ICT trading concepts (Expansion, Retracement, Reversal, Consolidation)
- `435949428-The-Ultimate-Guide-To-Order-Flow-Trading.pdf` - Order flow analysis patterns
- `Stops and Icebergs_ How to Detect Hidden Orders Using MBO Data.pdf` - Iceberg detection algorithms
- `Order Flow Patterns That Precede Big Reversals_From Aggressor Exhaustion to Iceberg Stacking.pdf` - Pattern recognition
- `Cracking the Spoofing Code_Inside the World of Market Manipulation.pdf` - Spoofing detection techniques

**Programming References:**

- `372759727-The-Python-Manual.pdf` - Python programming guide
- `powershell-scripting-powershell-7.5.pdf` - PowerShell scripting for Windows workflows
- `javascript.pdf` - JavaScript reference for web components

## MCP Server Setup for PDF Reading

To enable AI tools to read PDFs directly, configure MCP servers in VS Code settings.json:

```json
{
  "github.copilot.chat.mcpServers": {
    "pdf-reader": {
      "command": "C:\\Users\\Kudzai\\AppData\\Local\\Programs\\MCPPDFReader\\venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\Kudzai\\AppData\\Local\\Programs\\MCPPDFReader\\pdf_reader_server.py"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\Kudzai\\AppData\\Local\\Programs\\MCPPDFReader",
        "PDF_SOURCE_DIR": "F:\\TradingAgent\\deaProjects\\brapi-demo-consumer\\KnowledgeBase"
      }
    },
    "office-server": {
      "command": "python",
      "args": ["-m", "mcp_server_office"]
    }
  }
}
```

**Usage Examples:**

```powershell
# Extract text from any PDF in KnowledgeBase
mcp-pdf ocr "F:\TradingAgent\deaProjects\brapi-demo-consumer\KnowledgeBase\filename.pdf"

# Read specific trading concepts
mcp-pdf ocr "F:\TradingAgent\deaProjects\brapi-demo-consumer\KnowledgeBase\443878056-ICT-Mentorship-Month-1-Notes.pdf"

# Use PowerShell helper functions (load first: . .\scripts\pdf-helper.ps1)
Read-ICT                    # ICT Mentorship notes
Read-Bookmap               # Bookmap User Guide
Read-OrderFlow             # Order flow trading guide
Read-Spoofing              # Spoofing detection
Read-TimescaleDB           # Database setup
Read-Redis                 # Redis management
Read-JavaGuide             # Java development patterns
Read-KnowledgeBasePDF "search-term"  # Generic search

# Bulk operations
Read-AllPDFs               # Extract text from all 78 PDFs (takes time)
Read-AllDocs               # Same as above (alias)
Get-PDFSummary             # Quick overview of all PDFs with previews
Get-DocsSummary            # Same as above (alias)
```

**Natural Language Prompts for AI:**

- "Read the ICT trading notes" → AI should use ICT PDF
- "Show me the Bookmap API guide" → AI should use Bookmap User Guide PDF
- "Extract the order flow PDF" → AI should use order flow trading PDF
- "Analyze spoofing detection" → AI should use spoofing detection PDF
- "Get TimescaleDB setup info" → AI should use TimescaleDB guide PDF
- "Read all PDFs" → AI should process all 78 PDFs in KnowledgeBase
- "Summarize all documents" → AI should generate overview of all PDFs
- "Get docs summary" → AI should create quick overview with previews
