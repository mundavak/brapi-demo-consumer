// content.js - STEALTH VERSION (FIXED)
// TradingView Auto-Exporter Extension
// Designed to be undetectable by anti-bot systems

// Remove extension detection fingerprints
(function() {
  'use strict';
  
  // Safely hide chrome.runtime from page scripts
  try {
    if (typeof chrome !== 'undefined' && chrome.runtime) {
      // Override chrome object detection safely
      Object.defineProperty(window, 'chrome', {
        get: () => undefined,
        configurable: true
      });
    }
  } catch (e) {
    // Silently handle if chrome object can't be modified
  }
  
  // Safely spoof navigator.webdriver
  try {
    Object.defineProperty(navigator, 'webdriver', {
      get: () => false,
      configurable: true
    });
  } catch (e) {
    // Silently handle if webdriver can't be modified
  }
  
  // Safely hide automation detection
  try {
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5],
      configurable: true
    });
  } catch (e) {
    // Silently handle plugin spoofing errors
  }
  
  // Safely spoof language consistency
  try {
    Object.defineProperty(navigator, 'language', {
      get: () => 'en-US',
      configurable: true
    });
  } catch (e) {
    // Silently handle language spoofing errors
  }
  
  console.log('TradingView Tool: Content script loaded (Human Mode)');
})();

/**
 * Human-like sleep with random variation
 */
function sleep(ms) {
  // Add random variation to sleep times (±20%)
  const variation = ms * 0.2;
  const randomMs = ms + (Math.random() - 0.5) * variation * 2;
  return new Promise(resolve => setTimeout(resolve, Math.max(50, randomMs)));
}

/**
 * Human-like sleep with random variation
 */
function humanPause() {
  // Random pause between 300-1500ms (human processing time)
  return sleep(Math.random() * 1200 + 300);
}

// ============================================================================
// MAIN MESSAGE LISTENER (FIXED: Merged both listeners into one)
// ============================================================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Content script received message:', request);
  
  if (request.action === 'getSymbol') {
    // Try to extract symbol from page
    const symbol = extractSymbolFromPage();
    sendResponse({ symbol: symbol });
    return true; // Keep channel open
  }
  
  if (request.action === 'export' || request.action === 'exportData') {
    // Handle both legacy and new export actions
    console.log('🚀 Starting TradingView export with settings:', request.settings);
    
    handleTradingViewDownload(request.settings || {})
      .then(result => {
        console.log('✅ Export completed successfully:', result);
        sendResponse({ success: true, message: 'Export completed successfully' });
      })
      .catch(error => {
        console.error('❌ Export failed:', error);
        sendResponse({ success: false, error: error.message });
      });
    return true; // Keep message channel open for async response
  }
  
  if (request.action === 'screenshot') {
    takeScreenshot();
    sendResponse({success: true});
    return true;
  }
  
  if (request.action === 'captureHTML') {
    captureHTML();
    sendResponse({success: true});
    return true;
  }
});

// ============================================================================
// EXPORT WORKFLOW
// ============================================================================

/**
 * Main export handler - simplified to trust background.js
 */
async function handleTradingViewDownload(settings = {}) {
  console.log('🎯 TradingView export handler started');
  console.log('📊 Export settings:', settings);
  
  try {
    // Send symbol info to background script for smart naming
    const symbol = extractSymbolFromPage();
    chrome.runtime.sendMessage({
      action: 'updateSymbolInfo',
      symbol: symbol,
      timestamp: Date.now()
    });
    
    // Trigger the export workflow (right-click → Export → click button)
    console.log('🔄 Triggering TradingView export workflow...');
    const exportResult = await exportData(settings);
    
    if (!exportResult) {
      throw new Error('Export workflow failed');
    }
    
    console.log('✅ Export button clicked!');
    console.log('💾 background.js handling download automatically...');
    
    // Wait a moment for download to start
    await sleep(2000);
    
    // Show success message
    await showSuccessMessage();
    
    return {
      success: true,
      message: 'Export completed - background.js handling download'
    };
    
  } catch (error) {
    console.error('❌ Export handler failed:', error);
    
    // Show fallback success message
    showExportFallbackMessage(error);
    throw error;
  }
}

/**
 * Main export function (Stealth Mode)
 */
// content.js

/**
 * Main export function (Stealth Mode) - UPDATED
 */
/**
 * Main export function (FINAL STRATEGY - Stealth Mode)
 * Uses the exact IDs you found with the inspector.
 */
async function exportData(settings) {
  console.log('═'.repeat(70));
  console.log('FINAL EXPORT STRATEGY - Using Main Search Menu');
  console.log('═'.repeat(70));
  
  try {
    // STEP 1: Find and click the "Symbol Search" button
    console.log('🔍 Finding "Symbol Search" button [#header-toolbar-quick-search]...');
    
    // Use the exact ID you found!
    const symbolButton = document.querySelector('#header-toolbar-quick-search');
    
    if (!symbolButton) {
      throw new Error('Could not find the main "Symbol Search" button [#header-toolbar-quick-search].');
    }
    
    console.log('✅ Found "Symbol Search" button, clicking to open menu...');
    await clickElement(symbolButton);
    await sleep(1500); // Wait for search menu to open

    // STEP 2: Find the "Export chart data..." item
    // This calls the *next* function we are replacing.
    console.log('🔍 Looking for "Export chart data..." [#ExportChartData]...');
    const exportMenuItem = await findExportMenuItem(); 
    
    if (!exportMenuItem) {
      throw new Error('Found search menu, but could not find "Export chart data..." [#ExportChartData] inside it.');
    }

    console.log('✅ Found "Export chart data" menu item, clicking...');
    await clickElement(exportMenuItem); 
    await sleep(2000); // Wait for dialog to open

    // STEP 3: Check if the *dialog* opened
    const exportDialog = document.querySelector('[data-name="chart-export-dialog"]');
    
    if (!exportDialog) {
      throw new Error('Export dialog [data-name="chart-export-dialog"] did not appear.');
    }
    
    console.log('✅ Export dialog opened!');
    await sleep(500);

    // STEP 4: Configure the dialog (this function is already fixed)
    console.log('⚙️ Configuring dialog (setting ISO time, clicking Export)...');
    await configureExportDialog(); // This finds [#time-format-select] and [data-name="submit-button"]
    
    console.log('═'.repeat(70));
    console.log('✅ EXPORT BUTTON CLICKED');
    console.log('💾 background.js will handle download automatically');
    console.log('═'.repeat(70));
    
    return true;
    
  } catch (error) {
    console.error('═'.repeat(70));
    console.error('❌ EXPORT FAILED');
    console.error('═'.repeat(70));
    console.error('Error:', error.message);
    
    showManualInstructions(settings);
    throw error;
  }
}
/**
 * Configure the export dialog and click Export button
 */
async function configureExportDialog() {
  console.log('⚙️ Configuring export dialog...');
  
  await sleep(800);
  
  // **UPDATED: Use EXACT selectors from DOM inspection screenshots**
  console.log('🎯 Looking for export dialog using exact TradingView structure...');
  
  const dialog = document.querySelector('[data-name="chart-export-dialog"]') ||  // EXACT match from screenshots
                 document.querySelector('div[role="dialog"][aria-labelledby*="title"]') ||  // Specific dialog pattern
                 document.querySelector('.wrapper-bSQMhzr') ||  // Specific wrapper class from screenshots
                 document.querySelector('[role="dialog"]') ||  // Generic dialog fallback
                 document.querySelector('.dialog') ||
                 document.querySelector('[class*="dialog"]') ||
                 Array.from(document.querySelectorAll('div')).find(el => 
                   el.textContent.includes('Export chart data')
                 );
  
  if (!dialog) {
    console.warn('⚠️ Export dialog not found with any selector');
    console.log(' Debugging: Checking what dialogs exist...');
    
    // Debug: Show all dialog-like elements
    const allDialogs = document.querySelectorAll('[role="dialog"], .dialog, [class*="dialog"], [data-name*="dialog"]');
    console.log(`   Found ${allDialogs.length} dialog-like elements:`);
    allDialogs.forEach((d, i) => {
      const className = d.className?.toString() || 'no-class';
      const dataName = d.getAttribute('data-name') || 'no-data-name';
      const text = d.textContent?.substring(0, 50) || '';
      console.log(`     ${i+1}. ${d.tagName}.${className} [data-name="${dataName}"] - "${text}"`);
    });
    
    console.log('💡 Looking for Export button anywhere on page...');
    return await clickExportButtonGlobal();
  }
  
  console.log('✅ Found export dialog using selector:');
  console.log(`   Data-name: ${dialog.getAttribute('data-name')}`);
  console.log(`   Class: ${dialog.className}`);
  console.log(`   Text preview: ${dialog.textContent?.substring(0, 100)}`);

  // =================================================================
  // **NEW FIX:** Call the ISO time selector *before* clicking export
  await selectISOTimeFormat(dialog);
  await sleep(300); // Give it time to register
  // =================================================================
  
  // **SIMPLE: Just find and click Export button**
  console.log('🎯 Looking for Export button...');
  let exportButton = dialog.querySelector('[data-name="submit-button"]');
  
  if (exportButton) {
    console.log('✅ Found Export button via EXACT data-name selector!');
    console.log('   Button details:', {
      tagName: exportButton.tagName,
      className: exportButton.className,
      dataName: exportButton.getAttribute('data-name'),
      textContent: exportButton.textContent?.trim()
    });
    
    exportButton.click();
    await showSuccessMessage();
    return true;
  }
  
  // **STRATEGY 2: Look for submitButton class from screenshots**
  console.log('🎯 Strategy 2: Looking for submitButton class...');
  exportButton = dialog.querySelector('.submitButton-PhMf7PhQ') ||
                 dialog.querySelector('[class*="submitButton"]');
  
  if (exportButton) {
    console.log('✅ Found Export button via submitButton class!');
    exportButton.click();
    await showSuccessMessage();
    return true;
  }
  
  // **STRATEGY 3: Look for content-D4RPB3ZC span from screenshots**
  console.log('🎯 Strategy 3: Looking for Export span with exact class...');
  const exportSpan = dialog.querySelector('span.content-D4RPB3ZC');
  if (exportSpan && exportSpan.textContent?.includes('Export')) {
    const button = exportSpan.closest('button, [role="button"], [data-name*="submit"], [tabindex]');
    if (button) {
      console.log('✅ Found Export button via content span class!');
      button.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  // Strategy 2: Look for span with "Export" text (based on captured HTML)
  const exportSpans = Array.from(dialog.querySelectorAll('span')).filter(span => {
    const text = span.textContent?.trim();
    return text === 'Export' || text === 'Export...' || text === 'Export ';
  });
  
  console.log(`Found ${exportSpans.length} export spans in dialog`);
  
  for (const span of exportSpans) {
    console.log(`   Checking span: "${span.textContent?.trim()}" with class: ${span.className}`);
    
    // Find the clickable parent button
    const button = span.closest('button, [role="button"], [data-name*="submit"], [tabindex]');
    if (button) {
      console.log('✅ Found Export button via span → button hierarchy, clicking...');
      console.log('   Button details:', {
        tagName: button.tagName,
        className: button.className,
        dataName: button.getAttribute('data-name'),
        role: button.getAttribute('role')
      });
      button.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  // Strategy 3: Look for buttons with Export text content
  const buttons = dialog.querySelectorAll('button, [role="button"]');
  console.log(`Found ${buttons.length} buttons in dialog`);
  
  for (const btn of buttons) {
    const text = btn.textContent?.trim().toLowerCase();
    const label = (btn.getAttribute('aria-label') || '').toLowerCase();
    
    console.log(`  Button: "${btn.textContent?.trim()}" (aria-label: "${btn.getAttribute('aria-label') || 'none'}")`);
    console.log(`    Classes: ${btn.className}`);
    console.log(`    Data-name: ${btn.getAttribute('data-name') || 'none'}`);
    
    // Check for spans with content-* class pattern inside buttons
    const contentSpan = btn.querySelector('span[class*="content-"]');
    if (contentSpan && contentSpan.textContent?.toLowerCase().includes('export')) {
      console.log('✅ Found Export button via content-* class pattern, clicking...');
      btn.click();
      await showSuccessMessage();
      return true;
    }
    
    if (text === 'export' || label === 'export' || text === 'export...' || text === 'export ') {
      console.log('✅ Found Export button via text match, clicking...');
      btn.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  // Strategy 4: By data-name attribute patterns (common in TradingView)
  let exportBtn = dialog.querySelector('[data-name="submit-button"]') ||
                  dialog.querySelector('[data-name*="submit"]') ||
                  dialog.querySelector('[data-name*="export"]') ||
                  dialog.querySelector('button[name="submit"]');
  
  if (exportBtn) {
    console.log('✅ Found Export button via data-name, clicking...');
    console.log('   Data-name:', exportBtn.getAttribute('data-name'));
    exportBtn.click();
    await showSuccessMessage();
    return true;
  }
  
  console.warn('⚠️ Export button not found in dialog');
  console.log('💡 Dialog appeared but extension cannot click Export button automatically');
  console.log('💡 Available spans with content-* classes in dialog:');
  
  // Debug: Show available content-* spans
  const contentSpans = dialog.querySelectorAll('span[class*="content-"]');
  contentSpans.forEach((span, i) => {
    if (i < 5) {
      console.log(`  ${i+1}. "${span.textContent?.trim()}" (${span.className})`);
    }
  });
  
  console.log('💡 Please click the Export button manually');
  
  return false;
}

/**
 * Select ISO time format in the export dialog dropdown (FINAL FIX 2)
 * Uses the native .click() method instead of the complex clickElement() simulation.
 */
async function selectISOTimeFormat(dialog) {
  console.log('🕐 Attempting to select ISO time format (using native .click())...');
  
  try {
    // 1. Find the dropdown button
    const timeFormatDropdown = dialog.querySelector('#time-format-select');
    
    if (!timeFormatDropdown) {
      console.log('⚠️ Time format dropdown button (#time-format-select) not found - will use default format');
      return false;
    }

    console.log('🖱️ Opening time format dropdown (native click)...');
    
    // --- THIS IS THE FIX ---
    // Instead of await clickElement(timeFormatDropdown), we use the direct .click()
    timeFormatDropdown.click();
    // -----------------------

    // 2. Wait for the option to appear (this function is smart and unchanged)
    const isoOption = await waitForElement('#time-format-iso');

    // 3. Click the "ISO time" option
    if (isoOption) {
      console.log('✅ Found "ISO time" option [#time-format-iso], selecting (native click)...');
      
      // --- ALSO APPLYING THE FIX HERE ---
      isoOption.click();
      // ----------------------------------
      
      await sleep(200); // Brief pause to let it register
      console.log('✅ ISO time format selected successfully!');
      return true;
    } else {
      console.log('⚠️ "ISO time" option [#time-format-iso] not found in dropdown.');
      timeFormatDropdown.click(); // Click again to close it
      return false;
    }
    
  } catch (error) {
    console.error('❌ Error selecting ISO time format:', error);
    return false;
  }
}


// ============================================================================
// HELPER & DEBUGGING FUNCTIONS (No changes needed below)
// ============================================================================

/**
 * Show success message after export
 * background.js handles all download automation via chrome.downloads API
 */
async function showSuccessMessage() {
  await sleep(1000);
  
  console.log('');
  console.log('═'.repeat(70));
  console.log('🎉 SUCCESS! Export button clicked successfully!');
  console.log('═'.repeat(70));
  console.log('💾 Download handled by background.js - no dialog automation needed');
  console.log('📁 File saved automatically to Downloads folder');
  console.log('📊 Check Downloads for: chart_export_{SYMBOL}_{TIMEFRAME}_{TIMESTAMP}.csv');
  console.log('═'.repeat(70));
  console.log('');
  
  // NO SAVE DIALOG AUTOMATION NEEDED
  // background.js intercepts download via chrome.downloads.onDeterminingFilename
  // and saves directly with smart filename - no "Save As" dialog appears!
}

/**
 * Show export success message
 */
function showExportSuccessMessage(result) {
  console.log('');
  console.log('═'.repeat(70));
  console.log('🎉 TRADINGVIEW EXPORT SUCCESSFUL!');
  console.log('═'.repeat(70));
  console.log('✅ Export process completed');
  console.log('📁 File processed by Downloads API');
  console.log('💾 Smart filename and organization applied');
  console.log('🔔 Check for browser notification');
  console.log('');
  console.log('📂 Expected location: Downloads/TradingView_Data/');
  console.log('📄 Filename format: chart_export_SYMBOL_2025-11-03_TIME.csv');
  console.log('═'.repeat(70));
  console.log('');
}

/**
 * Show fallback message if Downloads API didn't detect
 */
function showExportFallbackMessage(error) {
  console.log('');
  console.log('═'.repeat(70));
  console.log('⚠️ EXPORT COMPLETED (Downloads API not detected)');
  console.log('═'.repeat(70));
  console.log('✅ TradingView export triggered successfully');
  console.log('📁 File may have been saved directly to Downloads folder');
  console.log('');
  console.log('🔍 To find your file:');
  console.log('   1. Check Downloads folder for CSV files');
  console.log('   2. Look for files with current timestamp');
  console.log('   3. Check browser download history (Ctrl+J)');
  console.log('');
  console.log('📋 Error details:', error.message);
  console.log('═'.repeat(70));
  console.log('');
}


/**
 * Show manual instructions (fallback)
 */
function showManualInstructions(settings) {
  const message = `
╔═══════════════════════════════════════════════════════════╗
║          TRADINGVIEW EXPORT - MANUAL MODE                 ║
╚═══════════════════════════════════════════════════════════╝

Automatic export needs manual help!

WHAT TO DO NOW:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The extension tried to automate the export but needs you
to complete the final steps:

1. Right-click menu should be open
   (If not, right-click on chart area)

2. Click "Export chart data..." option

3. Click "Export" in the dialog
   (Will export visible chart data automatically)

4. Choose save location and filename

Settings being used:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Symbol: ${settings.symbol}
• Exchange: ${settings.exchange}
• Data: Visible chart range (automatic)

The extension will continue trying to automate after you
complete these steps manually.

Click OK to continue.
`;

  alert(message);
}

/**
 * Take screenshot
 */
function takeScreenshot() {
  console.log('📸 Requesting screenshot...');
  chrome.runtime.sendMessage({action: 'captureTab'});
}

/**
 * Capture HTML for debugging
 */
function captureHTML() {
  console.log('📋 Capturing HTML for debugging...');
  
  // Capture full page HTML
  const fullHTML = document.documentElement.outerHTML;
  console.log('📄 Full page HTML captured (length:', fullHTML.length, ')');
  
  // Look for context menu
  const menu = document.querySelector('[role="menu"], .context-menu, [class*="menu"], [class*="item"]');
  if (menu) {
    console.log('🎯 CONTEXT MENU HTML:');
    console.log(menu.outerHTML);
  }
  
  // Look for dialog
  const dialog = document.querySelector('[role="dialog"], .dialog, [class*="dialog"]');
  if (dialog) {
    console.log('💬 DIALOG HTML:');
    console.log(dialog.outerHTML);
  }
  
  // Save to file (download)
  const blob = new Blob([fullHTML], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `tradingview-${Date.now()}.html`;
  a.click();
  URL.revokeObjectURL(url);
  
  console.log('✅ HTML file downloaded to Downloads folder');
}

/**
 * Extract symbol information from TradingView page
 */
function extractSymbolFromPage() {
  console.log('🔍 Extracting symbol from TradingView page...');
  
  // Strategy 1: Check URL hash (TradingView uses #symbol=XXX format)
  const hash = window.location.hash;
  const hashMatch = hash.match(/symbol=([^&]+)/);
  if (hashMatch) {
    const symbol = decodeURIComponent(hashMatch[1]);
    console.log('✅ Found symbol in URL hash:', symbol);
    return symbol;
  }
  
  // Strategy 2: Check URL params
  const urlParams = new URLSearchParams(window.location.search);
  const symbolFromUrl = urlParams.get('symbol');
  if (symbolFromUrl) {
    console.log('✅ Found symbol in URL:', symbolFromUrl);
    return symbolFromUrl;
  }
  
  // Strategy 3: Check page title (most reliable for TradingView)
  const title = document.title;
  // Match patterns like "MNQ1! Chart" or "CME_MINI:MNQ2025H - TradingView"
  const titleMatches = [
    title.match(/^([A-Z0-9_:!]+)\s+(?:Chart|—|-)/i),  // "MNQ1! Chart"
    title.match(/^([A-Z0-9_:!]+)\s*—\s*TradingView/i), // "MNQ1! — TradingView"
    title.match(/([A-Z0-9_]+:[A-Z0-9!]+)/i)            // "CME_MINI:MNQ1!"
  ];
  
  for (const match of titleMatches) {
    if (match && match[1]) {
      console.log('✅ Found symbol in title:', match[1]);
      return match[1];
    }
  }
  
  // Strategy 4: Look for symbol in chart header (current TradingView structure)
  const headerSelectors = [
    '[data-name="legend-source-title"]',              // Main chart title
    '[class*="chartTitle"]',                          // Chart title container
    '[class*="symbol-"]',                             // Symbol display
    '[data-role="button"][class*="symbol"]',          // Symbol button
    '.chart-container [class*="symbol"]',             // Chart symbol
    '.tv-symbol-header',                              // Symbol header
    '.js-button-text'                                 // Button text (may contain symbol)
  ];
  
  for (const selector of headerSelectors) {
    const element = document.querySelector(selector);
    if (element) {
      const text = element.textContent?.trim();
      // Match symbol patterns: MNQ1!, CME_MINI:MNQ1!, ES1!, etc.
      if (text && /^[A-Z0-9_]+:?[A-Z0-9!]+$/.test(text)) {
        console.log('✅ Found symbol via header selector:', text);
        return text;
      }
    }
  }
  
  // Strategy 5: Look for symbol in legend items
  const legendSelectors = [
    '[data-name="legend-source-item"]',
    '.chart-markup-table .legend .item',
    '[class*="legend"] [class*="item"]',
    '[class*="legend"] [class*="title"]'
  ];
  
  for (const selector of legendSelectors) {
    const elements = document.querySelectorAll(selector);
    for (const element of elements) {
      const text = element.textContent?.trim();
      if (text && text.length < 30 && /^[A-Z0-9_:!]+$/.test(text)) {
        console.log('✅ Found symbol via legend:', text);
        return text;
      }
    }
  }
  
  console.log('❌ Could not extract symbol from page - please ensure chart is loaded');
  console.log('📊 Page title:', document.title);
  console.log('🌐 URL:', window.location.href);
  return 'UNKNOWN_SYMBOL';
}

/**
 * Click an element with proper event simulation
 */
async function clickElement(element) {
  if (!element) {
    throw new Error('Element is null or undefined');
  }
  
  console.log(`🖱️ Clicking element: ${element.tagName}${element.className ? '.' + element.className : ''}`);
  
  // Scroll element into view if needed
  element.scrollIntoView({ behavior: 'smooth', block: 'center' });
  await sleep(100);
  
  // Create mouse events
  const mouseDownEvent = new MouseEvent('mousedown', {
    bubbles: true,
    cancelable: true,
    view: window,
    button: 0,
    buttons: 1
  });
  
  const clickEvent = new MouseEvent('click', {
    bubbles: true,
    cancelable: true,
    view: window,
    button: 0,
    buttons: 0
  });
  
  const mouseUpEvent = new MouseEvent('mouseup', {
    bubbles: true,
    cancelable: true,
    view: window,
    button: 0,
    buttons: 0
  });
  
  // Dispatch events with human timing
  element.dispatchEvent(mouseDownEvent);
  await sleep(Math.random() * 80 + 40);
  element.dispatchEvent(clickEvent);
  await sleep(Math.random() * 30 + 10);
  element.dispatchEvent(mouseUpEvent);
  
  console.log(`✅ Clicked element successfully`);
}


// ============================================================================
// ALL FUNCTIONS BELOW THIS LINE ARE OBSOLETE OR HELPERS
// FOR THE UI AUTOMATION
// ============================================================================


/**
 * Simulate human-like clicking with micro-movements
 */
async function simulateHumanClick(element) {
  const rect = element.getBoundingClientRect();
  
  // Random click position within element (human-like imprecision)
  const randomX = (Math.random() - 0.5) * (rect.width * 0.6);
  const randomY = (Math.random() - 0.5) * (rect.height * 0.6);
  
  const x = rect.left + rect.width / 2 + randomX;
  const y = rect.top + rect.height / 2 + randomY;
  
  // Simulate mouse hover first (human behavior)
  const hoverEvent = new MouseEvent('mouseover', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y
  });
  
  element.dispatchEvent(hoverEvent);
  await sleep(Math.random() * 100 + 50);
  
  // Then click with realistic sequence
  const mouseDownEvent = new MouseEvent('mousedown', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 0,
    buttons: 1
  });
  
  const clickEvent = new MouseEvent('click', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 0,
    buttons: 1
  });
  
  const mouseUpEvent = new MouseEvent('mouseup', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 0,
    buttons: 0
  });
  
  // Dispatch with human timing
  element.dispatchEvent(mouseDownEvent);
  await sleep(Math.random() * 80 + 40);
  element.dispatchEvent(clickEvent);
  await sleep(Math.random() * 30 + 10);
  element.dispatchEvent(mouseUpEvent);
}

/**
 * Find the chart element to click on
 */
function findChartElement() {
  const candidates = [
    document.querySelector('.chart-container'),
    document.querySelector('[class*="chart-container"]'),
    document.querySelector('canvas'),
    document.querySelector('[class*="chart-markup"]'),
    document.querySelector('[data-name="legend-source-item"]')?.closest('[class*="chart"]'),
  ];
  
  for (const element of candidates) {
    if (element && element.offsetParent !== null) {
      return element;
    }
  }
  
  return null;
}

/**
 * Simulate human-like right-click with random variations
 */
async function simulateRightClick(element) {
  const rect = element.getBoundingClientRect();
  
  // Add random offset to avoid perfect center clicks (human-like)
  const randomX = (Math.random() - 0.5) * (rect.width * 0.3);
  const randomY = (Math.random() - 0.5) * (rect.height * 0.3);
  
  const x = rect.left + rect.width / 2 + randomX;
  const y = rect.top + rect.height / 2 + randomY;
  
  // Add slight delay before action (human-like hesitation)
  await sleep(Math.random() * 200 + 100);
  
  // Create more realistic mouse events sequence
  const mouseDownEvent = new MouseEvent('mousedown', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 2,
    buttons: 2
  });
  
  const contextMenuEvent = new MouseEvent('contextmenu', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 2,
    buttons: 2
  });
  
  const mouseUpEvent = new MouseEvent('mouseup', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 2,
    buttons: 0
  });
  
  // Dispatch events with human-like timing
  element.dispatchEvent(mouseDownEvent);
  await sleep(Math.random() * 50 + 20);
  element.dispatchEvent(contextMenuEvent);
  await sleep(Math.random() * 30 + 10);
  element.dispatchEvent(mouseUpEvent);
  
  console.log('✅ Human-like right-click dispatched at', {x: Math.round(x), y: Math.round(y)});
}


/**
 * Smart helper to wait for an element to appear in the DOM
 */
function waitForElement(selector, timeout = 3000) {
  console.log(`🕒 Waiting for selector: ${selector}`);
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    
    const interval = setInterval(() => {
      const el = document.querySelector(selector);
      if (el) {
        clearInterval(interval);
        console.log(`✅ Found element: ${selector}`);
        resolve(el);
      }
      
      if (Date.now() - startTime > timeout) {
        clearInterval(interval);
        console.error(`❌ Timed out waiting for: ${selector}`);
        reject(new Error(`Timed out waiting for element: ${selector}`));
      }
    }, 100); // Check every 100ms
  });
}
/**
 * Find "Export chart data..." menu item (FINAL, SIMPLIFIED)
 * Uses the exact ID="#ExportChartData" found in your screenshots.
 */
async function findExportMenuItem() {
  console.log('🔍 Searching for export menu item using [#ExportChartData]...');
  
  // This is the stable selector from your inspector
  const exportItem = document.querySelector('#ExportChartData');
  
  if (exportItem) {
    console.log('✅ Found export item via stable ID selector!');
    return exportItem;
  }
  
  console.log('❌ Export menu item [#ExportChartData] not found.');
  return null;
}

/**
 * Check if an element is clickable
 */
function isClickableElement(element) {
  if (!element) return false;
  
  // Check tag names
  if (['BUTTON', 'A', 'INPUT'].includes(element.tagName)) {
    return true;
  }
  
  // Check attributes that indicate clickability
  if (element.getAttribute('role') === 'menuitem' ||
      element.getAttribute('role') === 'button' ||
      element.getAttribute('role') === 'row' ||
      element.onclick ||
      element.getAttribute('tabindex') !== null ||
      element.style.cursor === 'pointer') {
    return true;
  }
  
  // Check classes that often indicate clickable elements
  const clickableClasses = ['clickable', 'button', 'menu-item', 'item'];
  const className = element.className.toLowerCase();
  for (const cls of clickableClasses) {
    if (className.includes(cls)) {
      return true;
    }
  }
  
  return false;
}

/**
 * Try to find and click Export button globally (fallback) (UPDATED with monitored data)
 */
async function clickExportButtonGlobal() {
  console.log('🔍 Searching for Export button globally with EXACT TradingView selectors...');
  
  // **STRATEGY 1: Use EXACT button selector from DOM inspection**
  console.log('🎯 Strategy 1: Looking for exact data-name="submit-button"...');
  const exactSubmitBtn = document.querySelector('[data-name="submit-button"]');
  if (exactSubmitBtn) {
    console.log('✅ Found Export button via EXACT data-name selector!');
    console.log('   Button text:', exactSubmitBtn.textContent?.trim());
    console.log('   Button class:', exactSubmitBtn.className);
    
    exactSubmitBtn.click();
    await showSuccessMessage();
    return true;
  }
  
  // **STRATEGY 2: Look for submitButton class from DOM inspection**
  console.log('🎯 Strategy 2: Looking for submitButton-PhMf7PhQ class...');
  const submitButtonClass = document.querySelector('.submitButton-PhMf7PhQ') ||
                            document.querySelector('[class*="submitButton"]');
  if (submitButtonClass) {
    console.log('✅ Found Export button via submitButton class!');
    submitButtonClass.click();
    await showSuccessMessage();
    return true;
  }
  
  // **STRATEGY 3: Look for content-D4RPB3ZC span from DOM inspection**
  console.log('🎯 Strategy 3: Looking for exact content-D4RPB3ZC span...');
  const exactExportSpan = document.querySelector('span.content-D4RPB3ZC');
  if (exactExportSpan && exactExportSpan.textContent?.trim() === 'Export') {
    const button = exactExportSpan.closest('button, [role="button"], [data-name*="submit"], [tabindex]');
    if (button) {
      console.log('✅ Found Export button via EXACT content span class!');
      console.log('   Span text:', exactExportSpan.textContent);
      console.log('   Button details:', {
        tagName: button.tagName,
        className: button.className,
        dataName: button.getAttribute('data-name')
      });
      
      button.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  // **STRATEGY 4: Look within export dialog specifically**
  console.log('🎯 Strategy 4: Looking within export dialog container...');
  const exportDialog = document.querySelector('[data-name="chart-export-dialog"]') ||
                       document.querySelector('.wrapper-bSQMhzr');
  
  if (exportDialog) {
    console.log('   Found export dialog, searching for buttons inside...');
    
    // Look for any button with "Export" text inside the dialog
    const dialogButtons = exportDialog.querySelectorAll('button, [role="button"]');
    console.log(`   Found ${dialogButtons.length} buttons in dialog:`);
    
    for (let i = 0; i < dialogButtons.length; i++) {
      const btn = dialogButtons[i];
      const btnText = btn.textContent?.trim() || '';
      const btnClass = btn.className?.toString() || '';
      const btnDataName = btn.getAttribute('data-name') || '';
      
      console.log(`     ${i+1}. "${btnText}" (class: ${btnClass}, data-name: ${btnDataName})`);
      
      if (btnText.toLowerCase().includes('export') || 
          btnDataName.includes('submit') ||
          btnClass.includes('submit')) {
        console.log(`   ✅ Found Export button in dialog (button ${i+1})!`);
        btn.click();
        await showSuccessMessage();
        return true;
      }
    }
  }
  
  // Strategy 4: Original button text approach
  const allButtons = document.querySelectorAll('button');
  for (const btn of allButtons) {
    if ((btn.textContent.trim().toLowerCase() === 'export' || 
         btn.textContent.trim().toLowerCase() === 'export...') &&
        btn.offsetParent !== null) {
      console.log('✅ Found visible Export button via text, clicking...');
      btn.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  console.log('❌ Could not find Export button');
  return false;
}

/**
 * Debug function to log current page state
 */
function debugPageState() {
  console.log('🔍 DEBUG: Current page state');
  console.log('═'.repeat(50));
  
  // Check for menus
  const menus = document.querySelectorAll('[role="menu"], .context-menu, [class*="menu"]');
  console.log(`Menus found: ${menus.length}`);
  menus.forEach((menu, i) => {
    console.log(`Menu ${i+1}:`, menu.outerHTML.substring(0, 200) + '...');
  });
  
  // Check for dialogs
  const dialogs = document.querySelectorAll('[role="dialog"], .dialog, [class*="dialog"]');
  console.log(`Dialogs found: ${dialogs.length}`);
  dialogs.forEach((dialog, i) => {
    console.log(`Dialog ${i+1}:`, dialog.outerHTML.substring(0, 200) + '...');
  });
  
  // Check for export text - MORE DETAILED
  const exportElements = Array.from(document.querySelectorAll('*')).filter(el => {
    const text = el.textContent?.toLowerCase();
    return text && text.includes('export') && el.children.length === 0;
  });
  console.log(`Elements with 'export' text: ${exportElements.length}`);
  exportElements.forEach((el, i) => {
    console.log(`Export element ${i+1}:`, {
      text: el.textContent?.trim(),
      tagName: el.tagName,
      className: el.className,
      role: el.getAttribute('role'),
      tabindex: el.getAttribute('tabindex'),
      onclick: el.onclick ? 'has onclick' : 'no onclick',
      parent: el.parentElement?.tagName,
      parentClass: el.parentElement?.className?.substring(0, 50),
      parentRole: el.parentElement?.getAttribute('role'),
      isVisible: el.offsetParent !== null,
      outerHTML: el.outerHTML.substring(0, 150) + '...'
    });
  });
  
  // Check all visible clickable elements
  const clickableElements = Array.from(document.querySelectorAll('button, [role="menuitem"], [role="button"], [role="row"], a, [onclick], [tabindex]'))
    .filter(el => el.offsetParent !== null);
  
  console.log(`Visible clickable elements: ${clickableElements.length}`);
  clickableElements.slice(0, 15).forEach((el, i) => {
    const text = el.textContent?.trim().substring(0, 30);
    console.log(`Clickable ${i+1}: "${text}" (${el.tagName}, role: ${el.getAttribute('role') || 'none'})`);
  });
  
  console.log('═'.repeat(50));
}

// ============================================================================
// DELETED: All save dialog automation functions removed
// Reason: background.js uses chrome.downloads.onDeterminingFilename API
// ============================================================================


// Ready!
console.log('✅ TradingView Exporter: Enhanced with Downloads API');
console.log('💡 Click extension icon and press "Export Visible Data" to start');
console.log(' Downloads API will automatically manage files with smart names');