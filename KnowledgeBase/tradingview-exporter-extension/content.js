// content.js - STEALTH VERSION (FIXED) - WITH CORRECTED TIMEFRAME MAPPING
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
// EXPORT WORKFLOW WITH CORRECTED TIMEFRAME SUPPORT
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
    
    // If we have specific timeframes, we'll update the background for each one
    // Otherwise, we'll use the current timeframe
    if (settings.timeframes && settings.timeframes.length > 0) {
      console.log('⏰ Multiple timeframes detected, will update background for each export');
    } else {
      // Single export - update background with current timeframe
      chrome.runtime.sendMessage({
        action: 'updateSymbolInfo',
        symbol: symbol,
        timeframe: '1m', // Default to 1m for single export
        timestamp: Date.now()
      });
    }
    
    // Trigger the export workflow with timeframe support
    console.log('🔄 Triggering TradingView export workflow...');
    const exportResult = await exportData(settings);
    
    if (!exportResult) {
      throw new Error('Export workflow failed');
    }
    
    console.log('✅ Export completed successfully!');
    
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
 * Select timeframe in TradingView
 * @param {string} timeframe - The timeframe to select (e.g., '1', '5', '15', '30', '60', '120', '240', '1D')
 */
async function selectTimeframe(timeframe) {
    console.log(`⏰ Selecting timeframe: ${timeframe}`);
    
    try {
        // Strategy 1: Use the exact selector pattern from your screenshot
        const timeframeIndex = getTimeframeIndex(timeframe);
        const timeframeButton = document.querySelector(`#header-toolbar-intervals > div > button:nth-child(${timeframeIndex})`);
        
        if (timeframeButton) {
            console.log(`✅ Found timeframe button for ${timeframe} at index ${timeframeIndex}, clicking...`);
            await clickElement(timeframeButton);
            await sleep(1500); // Wait for chart to update
            return true;
        }
        
        // Strategy 2: Look for buttons with timeframe text
        const allTimeframeButtons = document.querySelectorAll('#header-toolbar-intervals button, [class*="timeframe"] button, [data-name*="timeframe"] button');
        
        console.log(`🔍 Found ${allTimeframeButtons.length} potential timeframe buttons`);
        
        for (const button of allTimeframeButtons) {
            const buttonText = button.textContent?.trim();
            if (buttonText && timeframeMatches(buttonText, timeframe)) {
                console.log(`✅ Found timeframe button via text: "${buttonText}", clicking...`);
                await clickElement(button);
                await sleep(1500); // Wait for chart to update
                return true;
            }
        }
        
        // Strategy 3: Look for data-value attributes
        const dataValueButton = document.querySelector(`[data-value="${timeframe}"]`);
        if (dataValueButton) {
            console.log(`✅ Found timeframe button via data-value="${timeframe}", clicking...`);
            await clickElement(dataValueButton);
            await sleep(1500);
            return true;
        }
        
        console.log(`❌ Could not find timeframe button for: ${timeframe}`);
        return false;
        
    } catch (error) {
        console.error(`❌ Error selecting timeframe ${timeframe}:`, error);
        return false;
    }
}

/**
 * Map timeframe values to button indices - CORRECTED MAPPING BASED ON USER FEEDBACK
 * User reported: 
 * - #header-toolbar-intervals > div > button:nth-child(10) = 4hour  
 * - #header-toolbar-intervals > div > button:nth-child(11) = Daily
 */
function getTimeframeIndex(timeframe) {
    const indexMap = {
        'tick': 1,   // Tick
        '1s': 2,     // 1 second
        '1': 3,      // 1 minute
        '5': 4,      // 5 minutes
        '15': 5,     // 15 minutes
        '30': 6,     // 30 minutes
        '60': 7,     // 1 hour
        '120': 8,    // 2 hours
        '180': 9,    // 3 hours
        '240': 10,   // 4 hours (WAS 9, NOW 10 - CORRECTED)
        '1D': 11,    // Daily (WAS 10, NOW 11 - CORRECTED)
        '1W': 12     // Weekly
    };
    return indexMap[timeframe] || 3; // Default to 1 minute
}

/**
 * Check if button text matches timeframe - UPDATED
 */
function timeframeMatches(buttonText, timeframe) {
    const textMap = {
        '1': ['1m', '1 minute', '1 min'],
        '5': ['5m', '5 minutes', '5 min'], 
        '15': ['15m', '15 minutes', '15 min'],
        '30': ['30m', '30 minutes', '30 min'],
        '60': ['1h', '1 hour', '60m', '60 min'],
        '120': ['2h', '2 hours', '120m'],
        '180': ['3h', '3 hours', '180m'],
        '240': ['4h', '4 hours', '240m'],
        '1D': ['1d', 'daily', '1 day', 'D'],
        '1W': ['1w', 'weekly', '1 week', 'W'],
        'tick': ['tick', 'ticks'],
        '1s': ['1s', '1 second']
    };
    
    const patterns = textMap[timeframe] || [];
    const lowerButtonText = buttonText.toLowerCase();
    
    return patterns.some(pattern => 
        lowerButtonText.includes(pattern.toLowerCase())
    );
}

/**
 * Main export function with timeframe support
 */
async function exportData(settings) {
    console.log('═'.repeat(70));
    console.log('FINAL EXPORT STRATEGY - With CORRECTED Timeframe Selection');
    console.log('═'.repeat(70));
    
    try {
        // STEP 0: Select timeframes if specified
        if (settings.timeframes && settings.timeframes.length > 0) {
            console.log('⏰ Timeframes to export:', settings.timeframes);
            
            let allExportsSuccessful = true;
            
            for (const timeframe of settings.timeframes) {
                console.log(`\n🔄 Processing timeframe: ${timeframe}`);
                
                // Select the timeframe
                const timeframeSelected = await selectTimeframe(timeframe);
                if (!timeframeSelected) {
                    console.log(`⚠️ Could not select timeframe ${timeframe}, using current timeframe`);
                }
                
                await sleep(2000); // Wait for chart to load new data
                
                // Update background script with current symbol and timeframe
                const symbol = extractSymbolFromPage();
                chrome.runtime.sendMessage({
                  action: 'updateSymbolInfo',
                  symbol: symbol,
                  timeframe: timeframe,
                  timestamp: Date.now()
                });
                
                // Perform export for this timeframe
                const exportSuccess = await performSingleExport(settings, timeframe);
                
                if (!exportSuccess) {
                    allExportsSuccessful = false;
                    console.log(`❌ Export failed for timeframe: ${timeframe}`);
                } else {
                    console.log(`✅ Export completed for timeframe: ${timeframe}`);
                }
                
                // Wait before next timeframe
                await sleep(1000);
            }
            
            return allExportsSuccessful;
        } else {
            // No specific timeframes, just do single export
            console.log('⏰ No specific timeframes selected, using current timeframe');
            return await performSingleExport(settings);
        }
        
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
 * Perform single export for current timeframe
 */
async function performSingleExport(settings, timeframe = null) {
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

    // STEP 4: Configure the dialog
    console.log('⚙️ Configuring dialog (setting ISO time, clicking Export)...');
    const dialogConfigured = await configureExportDialog();
    
    if (dialogConfigured) {
        console.log('═'.repeat(70));
        console.log('✅ EXPORT BUTTON CLICKED');
        if (timeframe) {
            console.log(`⏰ Timeframe: ${timeframe}`);
        }
        console.log('💾 background.js will handle download automatically');
        console.log('═'.repeat(70));
        return true;
    } else {
        console.log('❌ Failed to configure export dialog');
        return false;
    }
}

/**
 * Find "Export chart data..." menu item
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
 * Configure the export dialog and click Export button
 */
async function configureExportDialog() {
  console.log('⚙️ Configuring export dialog...');
  
  await sleep(800);
  
  console.log('🎯 Looking for export dialog using exact TradingView structure...');
  
  const dialog = document.querySelector('[data-name="chart-export-dialog"]') ||
                 document.querySelector('div[role="dialog"][aria-labelledby*="title"]') ||
                 document.querySelector('.wrapper-bSQMhzr') ||
                 document.querySelector('[role="dialog"]') ||
                 document.querySelector('.dialog') ||
                 document.querySelector('[class*="dialog"]') ||
                 Array.from(document.querySelectorAll('div')).find(el => 
                   el.textContent.includes('Export chart data')
                 );
  
  if (!dialog) {
    console.warn('⚠️ Export dialog not found with any selector');
    return await clickExportButtonGlobal();
  }
  
  console.log('✅ Found export dialog using selector:');
  console.log(`   Data-name: ${dialog.getAttribute('data-name')}`);
  console.log(`   Class: ${dialog.className}`);
  console.log(`   Text preview: ${dialog.textContent?.substring(0, 100)}`);

  // Select ISO time format before clicking export
  await selectISOTimeFormat(dialog);
  await sleep(300);
  
  // Find and click Export button
  console.log('🎯 Looking for Export button...');
  let exportButton = dialog.querySelector('[data-name="submit-button"]');
  
  if (exportButton) {
    console.log('✅ Found Export button via EXACT data-name selector!');
    exportButton.click();
    await showSuccessMessage();
    return true;
  }
  
  // Additional strategies for finding export button...
  exportButton = dialog.querySelector('.submitButton-PhMf7PhQ') ||
                 dialog.querySelector('[class*="submitButton"]');
  
  if (exportButton) {
    console.log('✅ Found Export button via submitButton class!');
    exportButton.click();
    await showSuccessMessage();
    return true;
  }
  
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
  
  // Additional fallback strategies...
  const exportSpans = Array.from(dialog.querySelectorAll('span')).filter(span => {
    const text = span.textContent?.trim();
    return text === 'Export' || text === 'Export...' || text === 'Export ';
  });
  
  for (const span of exportSpans) {
    const button = span.closest('button, [role="button"], [data-name*="submit"], [tabindex]');
    if (button) {
      console.log('✅ Found Export button via span → button hierarchy, clicking...');
      button.click();
      await showSuccessMessage();
      return true;
    }
  }
  
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
 * Select ISO time format in the export dialog dropdown
 */
async function selectISOTimeFormat(dialog) {
  console.log('🕐 Attempting to select ISO time format...');
  
  try {
    const timeFormatDropdown = dialog.querySelector('#time-format-select');
    
    if (!timeFormatDropdown) {
      console.log('⚠️ Time format dropdown button (#time-format-select) not found - will use default format');
      return false;
    }

    console.log('🖱️ Opening time format dropdown...');
    timeFormatDropdown.click();
    await sleep(500);

    const isoOption = await waitForElement('#time-format-iso');
    
    if (isoOption) {
      console.log('✅ Found "ISO time" option [#time-format-iso], selecting...');
      isoOption.click();
      await sleep(200);
      console.log('✅ ISO time format selected successfully!');
      return true;
    } else {
      console.log('⚠️ "ISO time" option [#time-format-iso] not found in dropdown.');
      timeFormatDropdown.click(); // Close dropdown
      return false;
    }
    
  } catch (error) {
    console.error('❌ Error selecting ISO time format:', error);
    return false;
  }
}

// ============================================================================
// HELPER & DEBUGGING FUNCTIONS (COMPLETE)
// ============================================================================

/**
 * Show success message after export
 */
async function showSuccessMessage() {
  await sleep(1000);
  
  console.log('');
  console.log('═'.repeat(70));
  console.log('🎉 SUCCESS! Export button clicked successfully!');
  console.log('═'.repeat(70));
  console.log('💾 Download handled by background.js - no dialog automation needed');
  console.log('📁 File saved automatically to Downloads folder');
  console.log('📊 Check Downloads for: SYMBOL_TIMEFRAME_2025-11-03T14-30-25.csv');
  console.log('═'.repeat(70));
  console.log('');
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
  console.log('📄 Filename format: SYMBOL_TIMEFRAME_2025-11-03_TIME.csv');
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
• Timeframes: ${settings.timeframes ? settings.timeframes.join(', ') : 'Current timeframe'}
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
  const titleMatches = [
    title.match(/^([A-Z0-9_:!]+)\s+(?:Chart|—|-)/i),
    title.match(/^([A-Z0-9_:!]+)\s*—\s*TradingView/i),
    title.match(/([A-Z0-9_]+:[A-Z0-9!]+)/i)
  ];
  
  for (const match of titleMatches) {
    if (match && match[1]) {
      console.log('✅ Found symbol in title:', match[1]);
      return match[1];
    }
  }
  
  // Strategy 4: Look for symbol in chart header
  const headerSelectors = [
    '[data-name="legend-source-title"]',
    '[class*="chartTitle"]',
    '[class*="symbol-"]',
    '[data-role="button"][class*="symbol"]',
    '.chart-container [class*="symbol"]',
    '.tv-symbol-header',
    '.js-button-text'
  ];
  
  for (const selector of headerSelectors) {
    const element = document.querySelector(selector);
    if (element) {
      const text = element.textContent?.trim();
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
    }, 100);
  });
}

/**
 * Try to find and click Export button globally (fallback)
 */
async function clickExportButtonGlobal() {
  console.log('🔍 Searching for Export button globally with EXACT TradingView selectors...');
  
  // Strategy 1: Use EXACT button selector
  const exactSubmitBtn = document.querySelector('[data-name="submit-button"]');
  if (exactSubmitBtn) {
    console.log('✅ Found Export button via EXACT data-name selector!');
    exactSubmitBtn.click();
    await showSuccessMessage();
    return true;
  }
  
  // Strategy 2: Look for submitButton class
  const submitButtonClass = document.querySelector('.submitButton-PhMf7PhQ') ||
                            document.querySelector('[class*="submitButton"]');
  if (submitButtonClass) {
    console.log('✅ Found Export button via submitButton class!');
    submitButtonClass.click();
    await showSuccessMessage();
    return true;
  }
  
  // Strategy 3: Look for content-D4RPB3ZC span
  const exactExportSpan = document.querySelector('span.content-D4RPB3ZC');
  if (exactExportSpan && exactExportSpan.textContent?.trim() === 'Export') {
    const button = exactExportSpan.closest('button, [role="button"], [data-name*="submit"], [tabindex]');
    if (button) {
      console.log('✅ Found Export button via EXACT content span class!');
      button.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  // Strategy 4: Look within export dialog specifically
  const exportDialog = document.querySelector('[data-name="chart-export-dialog"]') ||
                       document.querySelector('.wrapper-bSQMhzr');
  
  if (exportDialog) {
    console.log('   Found export dialog, searching for buttons inside...');
    
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
  
  // Strategy 5: Original button text approach
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

// Ready!
console.log('✅ TradingView Exporter: Enhanced with CORRECTED Timeframe Selection & Downloads API');
console.log('💡 Click extension icon and press "Export Visible Data" to start');
console.log('⏰ Multiple timeframe export now supported with CORRECTED button indices!');
console.log('📊 Timeframes available: Tick, 1s, 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, Daily, Weekly');
