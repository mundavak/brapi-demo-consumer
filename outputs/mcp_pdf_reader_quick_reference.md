# MCP PDF Reader - Quick Reference Guide

**Generated:** 2025-10-29  
**Installation:** C:\Users\Kudzai\AppData\Local\Programs\MCPPDFReader  
**Default PDF Dir:** F:\TradingAgent\deaProjects\brapi-demo-consumer

---

## 🚀 Quick Start

### Using with AI (GitHub Copilot) - RECOMMENDED

```
Just ask Copilot naturally:
"Read the Bookmap User Guide PDF and explain absorption"
"Extract ICT trading concepts from the mentorship PDF"
"Analyze all order flow PDFs in KnowledgeBase"
```

**Copilot automatically uses MCP tools - no commands needed!**

### Using CLI (Manual)

```powershell
# Extract text from PDF
mcp-pdf extract "KnowledgeBase/Bookmap-User-Guide-6-1.pdf"

# OCR for scanned PDFs
mcp-pdf ocr "scanned_document.pdf"

# Analyze PDF structure
mcp-pdf analyze "report.pdf"

# List all PDFs
mcp-pdf list

# Process all PDFs in directory
mcp-pdf batch KnowledgeBase/
```

---

## 📋 Available Commands

| Command                  | Purpose          | Example                       |
| ------------------------ | ---------------- | ----------------------------- |
| `mcp-pdf extract <file>` | Extract text     | `mcp-pdf extract file.pdf`    |
| `mcp-pdf ocr <file>`     | OCR extraction   | `mcp-pdf ocr scan.pdf`        |
| `mcp-pdf analyze <file>` | Get metadata     | `mcp-pdf analyze doc.pdf`     |
| `mcp-pdf list [dir]`     | List PDFs        | `mcp-pdf list KnowledgeBase/` |
| `mcp-pdf batch [dir]`    | Bulk process     | `mcp-pdf batch .`             |
| `mcp-pdf server`         | Start MCP server | `mcp-pdf server`              |
| `mcp-pdf help`           | Show help        | `mcp-pdf help`                |

---

## 🔧 MCP Tools (AI Uses These)

### 1. extract_text(file_path)

- **Purpose:** Extract native PDF text
- **Use Case:** Born-digital PDFs with selectable text
- **Returns:** JSON with pages, text, word_count

### 2. ocr(file_path)

- **Purpose:** Extract text using Tesseract OCR
- **Use Case:** Scanned PDFs, images in PDFs
- **Returns:** JSON with OCR text

### 3. analyze(file_path)

- **Purpose:** Get PDF metadata and structure
- **Use Case:** Understanding PDF before reading
- **Returns:** JSON with page_count, metadata, pages_info

### 4. list_pdfs()

- **Purpose:** List all PDFs in directory
- **Use Case:** Discovering available PDFs
- **Returns:** List of PDF filenames

---

## 📂 File Locations

### Installation

```
C:\Users\Kudzai\AppData\Local\Programs\MCPPDFReader\
├── pdf_reader_server.py   ← Main MCP server
├── mcp_wrapper.py          ← Currently active (VS Code config)
├── pdf_processor.py        ← Core PDF logic
├── mcp-pdf.bat            ← CLI wrapper
├── mcp-pdf.ps1            ← PowerShell implementation
└── venv/                  ← Python environment
```

### Your PDFs

```
F:\TradingAgent\deaProjects\brapi-demo-consumer\
└── KnowledgeBase\         ← 78 PDFs (ICT, Bookmap, Order Flow, etc.)
```

### Output Storage

```
F:\TradingAgent\deaProjects\brapi-demo-consumer\
└── outputs\
    └── pdf_extracts\      ← Extracted PDF content (JSON)
```

---

## 💡 Common Workflows

### Workflow 1: Read Single PDF with AI

```
User: "Read the ICT Mentorship PDF"
AI: [Automatically calls extract_text()]
AI: [Returns summary of ICT concepts]
```

### Workflow 2: Extract Single PDF to File

```powershell
mcp-pdf extract "KnowledgeBase/ICT-Mentorship.pdf" > outputs/ict_extracted.json
```

### Workflow 3: Process All PDFs in Folder

```powershell
mcp-pdf batch KnowledgeBase/
# Output: Progress for each PDF
```

### Workflow 4: OCR Scanned Trading Chart

```powershell
mcp-pdf ocr "scanned_chart.pdf"
```

### Workflow 5: List Available PDFs

```powershell
mcp-pdf list KnowledgeBase/
# Output: Found 78 PDFs...
```

---

## 🎯 AI Prompt Templates

### For Reading Specific PDF

```
"Read [PDF_NAME] and extract information about [TOPIC]"
"Summarize the key points in [PDF_NAME]"
"Find sections related to [KEYWORD] in [PDF_NAME]"
```

### For Multiple PDFs

```
"Read all PDFs in KnowledgeBase related to [TOPIC]"
"Compare [PDF1] and [PDF2] on [SUBJECT]"
"Extract all mentions of [KEYWORD] across all PDFs"
```

### For Dashboard Integration

```
"Extract ICT trading methodology from PDFs to improve dashboard signals"
"Build a pattern library from all order flow PDFs"
"Find absorption explanations in Bookmap PDFs"
```

---

## 🗄️ Content Retention Strategies

### Strategy 1: Conversation Context (Easiest)

- **How:** Just read PDF with AI, content stays in conversation
- **Duration:** Until conversation ends
- **Best For:** Single-session analysis

### Strategy 2: File-based Storage (Recommended)

```powershell
# Extract to JSON
mcp-pdf extract "file.pdf" > outputs/pdf_extracts/file.json

# Load later
$content = Get-Content outputs/pdf_extracts/file.json | ConvertFrom-Json
```

### Strategy 3: Database Storage (Production)

```sql
-- Create table
CREATE TABLE pdf_content (
    id SERIAL PRIMARY KEY,
    file_path TEXT,
    extracted_text TEXT,
    metadata JSONB,
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert extracted content
INSERT INTO pdf_content (file_path, extracted_text, metadata)
VALUES ('file.pdf', '...', '...');
```

---

## ⚙️ Configuration

### VS Code Settings Location

```
%APPDATA%\Code\User\settings.json
```

### Current MCP Configuration

```json
{
  "github.copilot.chat.mcpServers": {
    "pdf-reader": {
      "command": "C:\\Users\\Kudzai\\AppData\\Local\\Programs\\MCPPDFReader\\venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\Kudzai\\AppData\\Local\\Programs\\MCPPDFReader\\mcp_wrapper.py"
      ],
      "cwd": "F:\\TradingAgent\\deaProjects\\brapi-demo-consumer",
      "env": {
        "PYTHONPATH": "C:\\Users\\Kudzai\\AppData\\Local\\Programs\\MCPPDFReader",
        "PDF_SOURCE_DIR": "F:\\TradingAgent\\deaProjects\\brapi-demo-consumer"
      }
    }
  }
}
```

---

## 🔍 Troubleshooting

### Problem: "Tesseract not found"

**Solution:** Install Tesseract OCR

```powershell
choco install tesseract
# Or download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### Problem: PDF not found

**Solution:** Use absolute path or ensure file is in default directory

```powershell
# Absolute path
mcp-pdf extract "C:\Full\Path\To\file.pdf"

# Or relative to default dir
mcp-pdf extract "KnowledgeBase/file.pdf"
```

### Problem: Poor OCR quality

**Solution:** Try different language or preprocess image

```powershell
# (Language support not yet in CLI, but in Python API)
```

### Problem: Server not responding

**Solution:** Restart VS Code or manually start server

```powershell
mcp-pdf server
```

---

## 📊 Performance Tips

### For Large PDFs (100+ pages)

- Extract to file first, then process
- Use page ranges if supported
- Process in batches

### For Bulk Processing (50+ PDFs)

- Use `mcp-pdf batch` command
- Monitor memory usage
- Process in chunks if needed

### For OCR (Slow)

- OCR is ~10x slower than text extraction
- Only use OCR for scanned documents
- Consider preprocessing images for better accuracy

---

## 🎓 Learning Resources

### Documentation Files (outputs/)

1. `mcp_understanding_confirmation_report.json` - Complete understanding
2. `mcp_pdf_reader_complete_usage_guide.json` - Detailed guide
3. `mcp_dashboard_integration_analysis.json` - Integration strategies

### Key Concepts

- **MCP:** Model Context Protocol (AI-tool communication protocol)
- **FastMCP:** Python framework for building MCP servers
- **OCR:** Optical Character Recognition (reading text from images)
- **PyMuPDF:** Python PDF library (fitz module)
- **Tesseract:** Open-source OCR engine

---

## 🚀 Next Steps

### Immediate Actions

1. ✅ Test with a sample PDF: `mcp-pdf extract "KnowledgeBase/[pick_one].pdf"`
2. ✅ Ask Copilot to read a PDF: "Read [PDF] and summarize"
3. ✅ Extract key PDFs to JSON files for permanent storage

### Short-term (This Week)

1. Extract all ICT/Order Flow/Bookmap PDFs to JSON
2. Create database table for trading knowledge
3. Build pattern library from PDFs

### Long-term (This Month)

1. Integrate PDF knowledge into dashboard analysis
2. Implement RAG (Retrieval-Augmented Generation) system
3. Set up continuous PDF knowledge updates

---

## 📞 Quick Reference Card

| Task                 | Command/Prompt                             |
| -------------------- | ------------------------------------------ |
| **Read PDF with AI** | "Read [file.pdf] and [what you want]"      |
| **Extract text**     | `mcp-pdf extract "file.pdf"`               |
| **OCR scan**         | `mcp-pdf ocr "file.pdf"`                   |
| **Get metadata**     | `mcp-pdf analyze "file.pdf"`               |
| **List PDFs**        | `mcp-pdf list`                             |
| **Bulk process**     | `mcp-pdf batch [directory]`                |
| **Save to file**     | `mcp-pdf extract "file.pdf" > output.json` |
| **Start server**     | `mcp-pdf server`                           |
| **Help**             | `mcp-pdf help`                             |

---

**Status:** ✅ MCP PDF Reader is installed, configured, and ready to use!  
**Default Directory:** F:\TradingAgent\deaProjects\brapi-demo-consumer  
**PDFs Available:** 78 trading-related PDFs in KnowledgeBase/  
**Integration:** Active with GitHub Copilot in VS Code

**Ready to read PDFs! Just ask Copilot naturally or use mcp-pdf commands.**
