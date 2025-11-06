# PDF Helper Functions for KnowledgeBase
# Usage: . .\scripts\pdf-helper.ps1  (to load functions)

$KNOWLEDGE_BASE = "F:\TradingAgent\deaProjects\brapi-demo-consumer\KnowledgeBase"

function Find-PDF {
    param(
        [string]$SearchTerm
    )
    
    $pdfs = Get-ChildItem -Path $KNOWLEDGE_BASE -Filter "*.pdf" | Where-Object {
        $_.Name -like "*$SearchTerm*" -or 
        $_.Name -like "*ICT*" -and $SearchTerm -like "*ICT*" -or
        $_.Name -like "*Bookmap*" -and $SearchTerm -like "*Bookmap*" -or
        $_.Name -like "*Order*Flow*" -and $SearchTerm -like "*order*flow*" -or
        $_.Name -like "*Redis*" -and $SearchTerm -like "*redis*" -or
        $_.Name -like "*TimescaleDB*" -and $SearchTerm -like "*timescale*"
    }
    
    return $pdfs
}

function Read-KnowledgeBasePDF {
    param(
        [string]$SearchTerm,
        [switch]$List,
        [switch]$All,
        [switch]$Summary
    )
    
    if ($List) {
        Write-Host "Available PDFs in KnowledgeBase:" -ForegroundColor Green
        Get-ChildItem -Path $KNOWLEDGE_BASE -Filter "*.pdf" | ForEach-Object {
            Write-Host "  - $($_.Name)" -ForegroundColor Cyan
        }
        return
    }
    
    if ($All) {
        Write-Host "Reading ALL PDFs in KnowledgeBase (78 files)..." -ForegroundColor Yellow
        Write-Host "This will take several minutes. Consider using -Summary for faster overview." -ForegroundColor Yellow
        
        $allPdfs = Get-ChildItem -Path $KNOWLEDGE_BASE -Filter "*.pdf"
        $results = @()
        
        foreach ($pdf in $allPdfs) {
            Write-Host "Processing: $($pdf.Name)" -ForegroundColor Cyan
            try {
                $result = mcp-pdf ocr "$($pdf.FullName)" | ConvertFrom-Json
                $results += [PSCustomObject]@{
                    FileName  = $pdf.Name
                    WordCount = $result.word_count
                    FirstPage = if ($result.ocr_pages.Count -gt 0) { $result.ocr_pages[0].text.Substring(0, [Math]::Min(200, $result.ocr_pages[0].text.Length)) + "..." } else { "No content" }
                    FullText  = $result.total_text
                }
            }
            catch {
                Write-Host "Error processing $($pdf.Name): $($_.Exception.Message)" -ForegroundColor Red
            }
        }
        
        return $results
    }
    
    if ($Summary) {
        Write-Host "Generating summary of all PDFs..." -ForegroundColor Green
        
        $allPdfs = Get-ChildItem -Path $KNOWLEDGE_BASE -Filter "*.pdf"
        $summaries = @()
        
        foreach ($pdf in $allPdfs) {
            Write-Host "Summarizing: $($pdf.Name)" -ForegroundColor Cyan
            try {
                $result = mcp-pdf ocr "$($pdf.FullName)" | ConvertFrom-Json
                $preview = if ($result.ocr_pages.Count -gt 0) { 
                    $result.ocr_pages[0].text.Substring(0, [Math]::Min(150, $result.ocr_pages[0].text.Length)) + "..."
                }
                else { 
                    "No content" 
                }
                
                $summaries += [PSCustomObject]@{
                    FileName  = $pdf.Name
                    Pages     = $result.ocr_pages.Count
                    WordCount = $result.word_count
                    Preview   = $preview
                }
            }
            catch {
                Write-Host "Error processing $($pdf.Name): $($_.Exception.Message)" -ForegroundColor Red
            }
        }
        
        return $summaries | Format-Table -AutoSize
    }
    
    $found = Find-PDF -SearchTerm $SearchTerm
    
    if ($found.Count -eq 0) {
        Write-Host "No PDF found matching: $SearchTerm" -ForegroundColor Red
        Write-Host "Try: Read-KnowledgeBasePDF -List" -ForegroundColor Yellow
        return
    }
    
    if ($found.Count -gt 1) {
        Write-Host "Multiple PDFs found:" -ForegroundColor Yellow
        $found | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Cyan }
        Write-Host "Please be more specific." -ForegroundColor Yellow
        return
    }
    
    $pdfPath = $found[0].FullName
    Write-Host "Reading: $($found[0].Name)" -ForegroundColor Green
    
    # Execute the MCP command
    mcp-pdf ocr "$pdfPath"
}

# Aliases for common documents
function Read-ICT { Read-KnowledgeBasePDF -SearchTerm "ICT" }
function Read-Bookmap { Read-KnowledgeBasePDF -SearchTerm "Bookmap-User-Guide" }
function Read-OrderFlow { Read-KnowledgeBasePDF -SearchTerm "Order-Flow-Trading" }
function Read-Spoofing { Read-KnowledgeBasePDF -SearchTerm "Spoofing" }
function Read-TimescaleDB { Read-KnowledgeBasePDF -SearchTerm "TimescaleDB" }
function Read-Redis { Read-KnowledgeBasePDF -SearchTerm "redis" }
function Read-JavaGuide { Read-KnowledgeBasePDF -SearchTerm "java-developers" }

# Bulk reading functions
function Read-AllPDFs { Read-KnowledgeBasePDF -All }
function Read-AllDocs { Read-KnowledgeBasePDF -All }
function Get-PDFSummary { Read-KnowledgeBasePDF -Summary }
function Get-DocsSummary { Read-KnowledgeBasePDF -Summary }

Write-Host "PDF Helper loaded! Available commands:" -ForegroundColor Green
Write-Host "  Read-KnowledgeBasePDF 'search-term'" -ForegroundColor Cyan
Write-Host "  Read-KnowledgeBasePDF -List" -ForegroundColor Cyan
Write-Host "  Read-AllPDFs / Read-AllDocs (reads all 78 PDFs)" -ForegroundColor Cyan
Write-Host "  Get-PDFSummary / Get-DocsSummary (quick overview)" -ForegroundColor Cyan
Write-Host "  Read-ICT, Read-Bookmap, Read-OrderFlow, Read-Spoofing" -ForegroundColor Cyan
Write-Host "  Read-TimescaleDB, Read-Redis, Read-JavaGuide" -ForegroundColor Cyan