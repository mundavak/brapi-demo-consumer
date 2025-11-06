// background.js - Service worker for TradingView Export with Advanced Downloads API

console.log('TradingView Exporter: Advanced Background Script Loaded');

// Download management state
let downloadQueue = new Map();
let autoDownloadSettings = {
  enabled: false,
  autoSave: true,
  downloadPath: 'TradingView_Data',
  filePrefix: 'chart_export_',
  enableNotifications: true
};

// Auto-screenshot state
let autoScreenshotActive = false;
let screenshotInterval = null;
let screenshotSettings = {};

// Initialize Downloads API monitoring
chrome.downloads.onCreated.addListener((downloadItem) => {
  console.log('📥 Download created:', downloadItem);
  
  // Check if this is our TradingView export
  if (downloadItem.url && downloadItem.url.includes('blob:') && 
      downloadItem.filename && downloadItem.filename.includes('.csv')) {
    
    console.log('🎯 TradingView CSV export detected');
    downloadQueue.set(downloadItem.id, {
      item: downloadItem,
      timestamp: Date.now(),
      type: 'tradingview_export'
    });
    
    // Auto-handle the download if enabled
    if (autoDownloadSettings.autoSave) {
      handleTradingViewDownload(downloadItem);
    }
  }
});

// Monitor download progress and completion
chrome.downloads.onChanged.addListener((downloadDelta) => {
  if (downloadQueue.has(downloadDelta.id)) {
    const download = downloadQueue.get(downloadDelta.id);
    
    if (downloadDelta.state && downloadDelta.state.current === 'complete') {
      console.log('✅ TradingView export completed:', download.item.filename);
      
      // Show success notification
      if (autoDownloadSettings.enableNotifications) {
        showDownloadNotification(download.item, 'completed');
      }
      
      // Clean up
      setTimeout(() => {
        downloadQueue.delete(downloadDelta.id);
      }, 5000);
    }
    
    if (downloadDelta.state && downloadDelta.state.current === 'interrupted') {
      console.log('❌ TradingView export failed:', downloadDelta.error);
      
      if (autoDownloadSettings.enableNotifications) {
        showDownloadNotification(download.item, 'failed', downloadDelta.error);
      }
    }
  }
});

// Handle filename customization for Downloads API
chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
  console.log('📝 Determining filename for download:', downloadItem);
  
  // Check if this is our TradingView export
  if (downloadItem.url && downloadItem.url.includes('blob:') && 
      downloadItem.filename && downloadItem.filename.includes('.csv')) {
    
    console.log('🎯 Customizing filename for TradingView export');
    
    // Generate smart filename
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
    const time = new Date().toTimeString().split(' ')[0].replace(/:/g, '');
    
    let symbol = autoDownloadSettings.currentSymbol || 'UNKNOWN';
    symbol = symbol.replace(/[^a-zA-Z0-9]/g, '_');
    
    const smartFilename = `${autoDownloadSettings.filePrefix}${symbol}_${timestamp}_${time}.csv`;
    const downloadPath = `${autoDownloadSettings.downloadPath}/${smartFilename}`;
    
    console.log(`📁 Smart filename: ${downloadPath}`);
    
    suggest({
      filename: downloadPath,
      conflictAction: 'uniquify'
    });
    
    return true;
  } else {
    // Not our export, use default filename
    suggest();
    return true;
  }
});

// Advanced download handler for TradingView exports
async function handleTradingViewDownload(downloadItem) {
  try {
    console.log('🚀 Auto-handling TradingView download...');
    
    // Generate smart filename with timestamp and symbol
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
    const time = new Date().toTimeString().split(' ')[0].replace(/:/g, '');
    
    // Try to get symbol from stored info or extract from page
    let symbol = 'UNKNOWN';
    
    // First try stored symbol from content script
    if (autoDownloadSettings.currentSymbol) {
      symbol = autoDownloadSettings.currentSymbol.replace(/[^a-zA-Z0-9]/g, '_');
      console.log('✅ Using stored symbol:', symbol);
    } else {
      // Fallback: try to extract from page
      try {
        const tabs = await chrome.tabs.query({active: true, currentWindow: true});
        if (tabs[0]) {
          const result = await chrome.tabs.sendMessage(tabs[0].id, {action: 'getSymbol'});
          if (result && result.symbol) {
            symbol = result.symbol.replace(/[^a-zA-Z0-9]/g, '_');
            console.log('✅ Extracted symbol from page:', symbol);
          }
        }
      } catch (e) {
        console.log('⚠️ Could not extract symbol, using default');
      }
    }
    
    // Smart filename: TradingView_BTCUSD_2025-11-03_143025.csv
    const smartFilename = `${autoDownloadSettings.filePrefix}${symbol}_${timestamp}_${time}.csv`;
    
    // Use Downloads API to programmatically manage the file
    const downloadPath = `${autoDownloadSettings.downloadPath}/${smartFilename}`;
    
    console.log(`📁 Saving to: ${downloadPath}`);
    
    // Show immediate notification
    if (autoDownloadSettings.enableNotifications) {
      showDownloadNotification(downloadItem, 'saving', null, smartFilename);
    }
    
    return true;
    
  } catch (error) {
    console.error('❌ Error handling TradingView download:', error);
    
    if (autoDownloadSettings.enableNotifications) {
      showDownloadNotification(downloadItem, 'error', error.message);
    }
    
    return false;
  }
}

// Show download notifications
function showDownloadNotification(downloadItem, status, error = null, filename = null) {
  let title, message, iconUrl;
  
  switch (status) {
    case 'saving':
      title = '💾 TradingView Export';
      message = `Auto-saving: ${filename || downloadItem.filename}`;
      iconUrl = 'icons/icon48.png';
      break;
      
    case 'completed':
      title = '✅ Export Complete';
      message = `Successfully saved: ${downloadItem.filename}`;
      iconUrl = 'icons/icon48.png';
      break;
      
    case 'failed':
      title = '❌ Export Failed';
      message = `Error: ${error || 'Unknown error'}`;
      iconUrl = 'icons/icon48.png';
      break;
      
    case 'error':
      title = '⚠️ Processing Error';
      message = `Auto-save error: ${error || 'Unknown error'}`;
      iconUrl = 'icons/icon48.png';
      break;
  }
  
  chrome.notifications.create({
    type: 'basic',
    iconUrl: iconUrl,
    title: title,
    message: message
  });
}

// Listen for messages from popup and content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received message:', request);
  
  // Handle auto-download settings
  if (request.action === 'updateAutoDownloadSettings') {
    autoDownloadSettings = { ...autoDownloadSettings, ...request.settings };
    console.log('✅ Auto-download settings updated:', autoDownloadSettings);
    sendResponse({success: true});
    return true;
  }
  
  // Handle download configuration
  if (request.action === 'configureDownloads') {
    configureDownloadSettings(request.config);
    sendResponse({success: true});
    return true;
  }
  
  // Handle symbol info updates from content script
  if (request.action === 'updateSymbolInfo') {
    console.log('📊 Received symbol info from content script:', request);
    
    // Store symbol info for smart filename generation
    autoDownloadSettings.currentSymbol = request.symbol;
    autoDownloadSettings.lastExportTime = request.timestamp;
    
    console.log('✅ Symbol info updated for smart naming:', {
      symbol: request.symbol,
      timestamp: new Date(request.timestamp).toLocaleString()
    });
    
    sendResponse({success: true});
    return true;
  }
  
  // Handle export request with Downloads API
  if (request.action === 'exportWithDownloadsAPI') {
    handleExportWithDownloadsAPI(request.settings)
      .then(result => {
        sendResponse(result);
      })
      .catch(error => {
        sendResponse({success: false, error: error.message});
      });
    return true; // Keep message channel open
  }
  
  // Legacy handlers
  if (request.action === 'startAuto') {
    startAutoScreenshot(request.settings);
    sendResponse({success: true});
  }
  
  if (request.action === 'stopAuto') {
    stopAutoScreenshot();
    sendResponse({success: true});
  }
  
  if (request.action === 'captureTab') {
    captureCurrentTab();
    sendResponse({success: true});
  }
});

// Configure download settings
function configureDownloadSettings(config) {
  console.log('📁 Configuring download settings:', config);
  
  if (config.downloadPath) {
    autoDownloadSettings.downloadPath = config.downloadPath;
  }
  
  if (config.filePrefix) {
    autoDownloadSettings.filePrefix = config.filePrefix;
  }
  
  if (typeof config.autoSave === 'boolean') {
    autoDownloadSettings.autoSave = config.autoSave;
  }
  
  if (typeof config.enableNotifications === 'boolean') {
    autoDownloadSettings.enableNotifications = config.enableNotifications;
  }
  
  console.log('✅ Updated settings:', autoDownloadSettings);
}

// Handle export with Downloads API
async function handleExportWithDownloadsAPI(settings) {
  console.log('🚀 Handling export with Downloads API...');
  
  try {
    // Find TradingView tab
    const tabs = await chrome.tabs.query({
      url: "*://www.tradingview.com/chart/*"
    });
    
    if (tabs.length === 0) {
      throw new Error('No TradingView tab found');
    }
    
    const tab = tabs[0];
    console.log('✅ Found TradingView tab:', tab.title);
    
    // Send export message to content script
    const result = await chrome.tabs.sendMessage(tab.id, {
      action: 'exportData',
      settings: settings
    });
    
    if (result && result.success) {
      console.log('✅ Export initiated successfully');
      return { success: true, message: 'Export started successfully' };
    } else {
      throw new Error(result?.error || 'Export failed');
    }
    
  } catch (error) {
    console.error('❌ Export with Downloads API failed:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Start auto-screenshot
 */
function startAutoScreenshot(settings) {
  console.log('Starting auto-screenshot with settings:', settings);
  
  autoScreenshotActive = true;
  screenshotSettings = settings;
  
  // Take screenshot every interval
  screenshotInterval = setInterval(() => {
    if (autoScreenshotActive) {
      takeScheduledScreenshot();
    }
  }, settings.interval * 1000);
  
  // Take first screenshot immediately
  takeScheduledScreenshot();
}

/**
 * Stop auto-screenshot
 */
function stopAutoScreenshot() {
  console.log('Stopping auto-screenshot');
  
  autoScreenshotActive = false;
  
  if (screenshotInterval) {
    clearInterval(screenshotInterval);
    screenshotInterval = null;
  }
}

/**
 * Take scheduled screenshot
 */
async function takeScheduledScreenshot() {
  console.log('Taking scheduled screenshot...');
  
  // Find TradingView tab
  const tabs = await chrome.tabs.query({url: "*://www.tradingview.com/chart/*"});
  
  if (tabs.length === 0) {
    console.warn('No TradingView tab found');
    return;
  }
  
  // Send message to content script
  chrome.tabs.sendMessage(tabs[0].id, {
    action: 'screenshot'
  });
}

/**
 * Trigger scheduled export
 */
async function triggerScheduledExport(timeframe) {
  console.log(`Triggering scheduled export for ${timeframe}`);
  
  // Get saved settings
  const settings = await chrome.storage.sync.get(['symbol', 'exchange', 'bars']);
  
  // Find TradingView tab
  const tabs = await chrome.tabs.query({url: "*://www.tradingview.com/chart/*"});
  
  if (tabs.length === 0) {
    console.warn('No TradingView tab found for scheduled export');
    return;
  }
  
  // Send message to content script
  chrome.tabs.sendMessage(tabs[0].id, {
    action: 'export',
    settings: {
      symbol: settings.symbol || 'NQ1!',
      exchange: settings.exchange || 'CME',
      bars: settings.bars || 1000,
      timeframes: [timeframe]
    }
  });
}

/**
 * Capture current tab screenshot
 */
async function captureCurrentTab() {
  try {
    const tabs = await chrome.tabs.query({active: true, currentWindow: true});
    
    if (tabs[0]) {
      const dataUrl = await chrome.tabs.captureVisibleTab(null, {
        format: 'png',
        quality: 100
      });
      
      // Download screenshot
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `tradingview_${timestamp}.png`;
      
      chrome.downloads.download({
        url: dataUrl,
        filename: `${screenshotSettings.saveLocation || 'tradingview_screenshots'}/${filename}`,
        saveAs: false
      });
      
      console.log('Screenshot saved:', filename);
    }
  } catch (error) {
    console.error('Failed to capture screenshot:', error);
  }
}

/**
 * Calculate next export time in ET timezone
 */
function getNextExportTime(hour, minute) {
  const now = new Date();
  
  // Convert to ET timezone (UTC-5 or UTC-4 depending on DST)
  const etOffset = -5; // EST (adjust for DST if needed)
  const etTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  
  // Set target time
  const target = new Date(etTime);
  target.setHours(hour, minute, 0, 0);
  
  // If target time has passed today, schedule for tomorrow
  if (target <= etTime) {
    target.setDate(target.getDate() + 1);
  }
  
  return target.getTime();
}

console.log('TradingView Exporter: Background ready');