// debug-export.js - Debug script to test export functionality
// Run this in the TradingView console to test the export process

console.log('🔧 TradingView Export Debug Script');
console.log('================================');

// Test 1: Check if extension is loaded
console.log('Test 1: Extension Detection');
if (typeof chrome !== 'undefined' && chrome.runtime) {
  console.log('✅ Chrome extension runtime detected');
  
  // Test messaging to background script
  chrome.runtime.sendMessage({action: 'updateSymbolInfo', symbol: 'TEST_SYMBOL', timestamp: Date.now()}, (response) => {
    if (response && response.success) {
      console.log('✅ Background script communication working');
    } else {
      console.log('❌ Background script communication failed');
    }
  });
} else {
  console.log('❌ Chrome extension runtime not detected');
}

// Test 2: Check Downloads API availability
console.log('\nTest 2: Downloads API');
if (typeof chrome !== 'undefined' && chrome.downloads) {
  console.log('✅ Downloads API available');
  
  // Test download permissions
  chrome.permissions.contains({permissions: ['downloads']}, (result) => {
    console.log('Downloads permission:', result ? '✅ Granted' : '❌ Not granted');
  });
} else {
  console.log('❌ Downloads API not available');
}

// Test 3: Symbol extraction
console.log('\nTest 3: Symbol Extraction');
function testSymbolExtraction() {
  // Strategy 1: Check URL params
  const urlParams = new URLSearchParams(window.location.search);
  const symbolFromUrl = urlParams.get('symbol');
  if (symbolFromUrl) {
    console.log('✅ Symbol from URL:', symbolFromUrl);
    return symbolFromUrl;
  }
  
  // Strategy 2: Check page title
  const title = document.title;
  const titleMatch = title.match(/([A-Z0-9]+)\s*(?:Chart|TradingView)/i);
  if (titleMatch) {
    console.log('✅ Symbol from title:', titleMatch[1]);
    return titleMatch[1];
  }
  
  // Strategy 3: Look for symbol display elements
  const symbolSelectors = [
    '[data-name="legend-source-item"]',
    '.chart-markup-table .legend .item',
    '.legend-TW8L5AjY .item-TW8L5AjY',
    '[class*="legend"] [class*="item"]',
    '[class*="symbol"]',
    '.tv-chart-header__symbol'
  ];
  
  for (const selector of symbolSelectors) {
    const element = document.querySelector(selector);
    if (element) {
      const text = element.textContent?.trim();
      if (text && text.length < 20 && /^[A-Z0-9:!]+$/.test(text)) {
        console.log('✅ Symbol from selector:', text);
        return text;
      }
    }
  }
  
  console.log('❌ Could not extract symbol');
  return 'UNKNOWN_SYMBOL';
}

const symbol = testSymbolExtraction();
console.log('Final symbol:', symbol);

// Test 4: Export button detection
console.log('\nTest 4: Export Button Detection');
function testExportButtonDetection() {
  // Look for layout button
  const layoutButton = document.querySelector('[data-name="save-load-menu-item-rename"]')?.closest('button') ||
                       document.querySelector('[aria-label*="layout"]') ||
                       document.querySelector('[data-tooltip*="layout"]') ||
                       document.querySelector('button[class*="button-mer"][class*="BkM5y"]') ||
                       Array.from(document.querySelectorAll('button')).find(btn => {
                         const text = btn.textContent?.trim();
                         const tooltip = btn.getAttribute('data-tooltip') || btn.getAttribute('aria-label') || '';
                         const hasNumber = text && /^\d+$/.test(text);
                         const hasLayoutKeyword = tooltip.toLowerCase().includes('layout') ||
                                                 tooltip.toLowerCase().includes('manage') ||
                                                 tooltip.toLowerCase().includes('save');
                         return hasNumber || hasLayoutKeyword;
                       });
  
  if (layoutButton) {
    console.log('✅ Layout button found:', layoutButton.textContent?.trim());
    console.log('   Class:', layoutButton.className);
    console.log('   Tooltip:', layoutButton.getAttribute('data-tooltip') || 'none');
  } else {
    console.log('❌ Layout button not found');
  }
  
  // Look for export dialog
  const exportDialog = document.querySelector('[data-name="chart-export-dialog"]');
  if (exportDialog) {
    console.log('✅ Export dialog found (already open)');
  } else {
    console.log('❌ Export dialog not found (not open)');
  }
}

testExportButtonDetection();

// Test 5: Blob URL monitoring
console.log('\nTest 5: Blob URL Monitoring');
const originalCreateObjectURL = URL.createObjectURL;
URL.createObjectURL = function(blob) {
  const url = originalCreateObjectURL.call(this, blob);
  
  console.log('🔍 Blob URL created:', {
    type: blob.type,
    size: blob.size,
    url: url.substring(0, 50) + '...'
  });
  
  if ((blob.type && blob.type.includes('csv')) || 
      (blob.type && blob.type.includes('text')) || 
      blob.size > 100) {
    console.log('🎯 CSV-like blob detected! This should trigger Downloads API');
  }
  
  return url;
};

console.log('✅ Blob monitoring enabled');

// Test 6: Manual export trigger
console.log('\nTest 6: Manual Export Test');
console.log('To test the export:');
console.log('1. Open this console (F12)');
console.log('2. Click the "Export Visible Data" button in your extension');
console.log('3. Watch this console for debug output');
console.log('4. Check the background script console (chrome://extensions -> Details -> Inspect views: background page)');

// Helper function to trigger export manually
window.testExport = function() {
  console.log('🚀 Triggering manual export test...');
  
  if (typeof chrome !== 'undefined' && chrome.runtime) {
    chrome.runtime.sendMessage({
      action: 'exportWithDownloadsAPI',
      settings: {
        symbol: symbol,
        exchange: 'NASDAQ',
        timeframes: ['1D']
      }
    }, (response) => {
      console.log('Export response:', response);
    });
  } else {
    console.log('❌ Cannot trigger export - extension not available');
  }
};

console.log('\n🎯 Run testExport() to manually trigger an export');
console.log('🎯 Or use the extension popup to click "Export Visible Data"');

console.log('\n================================');
console.log('🔧 Debug script loaded successfully');
console.log('Ready to test TradingView export functionality!');