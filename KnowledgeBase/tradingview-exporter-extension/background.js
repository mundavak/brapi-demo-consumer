// background.js - Service worker (FIXED & ENHANCED)
// Includes Advanced Downloads API & Daily Scheduler

console.log('TradingView Exporter: Advanced Background Script Loaded');

// --- Globals ---
let downloadQueue = new Map();
let autoDownloadSettings = {
  enabled: false,
  autoSave: true,
  downloadPath: 'TradingView_Data',
  filePrefix: 'chart_export_',
  enableNotifications: true,
  currentSymbol: 'UNKNOWN' // Stores symbol from content script
};

// The name for our daily alarm
const DAILY_EXPORT_ALARM_NAME = 'dailyTradingViewExport';


// =================================================================
// DAILY SCHEDULER (Alarm API)
// =================================================================

// 1. Listen for the alarm to fire
chrome.alarms.onAlarm.addListener((alarm) => {
  console.log('Alarm fired:', alarm.name);

  // Check if it's our daily export alarm
  if (alarm.name === DAILY_EXPORT_ALARM_NAME) {
    console.log('Triggering scheduled daily export for 5:45 PM EST...');
    
    // Call the function that knows how to
    // find the TradingView tab and send the export message.
    handleExportWithDownloadsAPI({})
      .then(() => console.log('Scheduled export initiated successfully.'))
      .catch(err => console.error('Scheduled export FAILED:', err));
  }
});


// 2. Create the alarm when the extension is installed or updated
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed/updated. Setting up daily alarm...');
  createDailyAlarm();
});

// 3. Helper function to create the alarm
function createDailyAlarm() {
  const H = 17; // 5 PM (in 24-hour format)
  const M = 45; // 45 minutes

  // We use your existing function to get the next 5:45 PM EST
  const nextAlarmTime = getNextExportTime(H, M);
  
  // Create the alarm
  chrome.alarms.create(DAILY_EXPORT_ALARM_NAME, {
    when: nextAlarmTime,          // The first time to run
    periodInMinutes: 24 * 60    // 1440 minutes = 24 hours, to repeat daily
  });

  console.log(`✅ Daily export alarm created. Next run: ${new Date(nextAlarmTime).toLocaleString()}`);
}

/**
 * Calculate next export time in ET timezone
 */
function getNextExportTime(hour, minute) {
  // Get the current time in the 'America/New_York' timezone
  const etTime = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
  
  // Set target time
  const target = new Date(etTime);
  target.setHours(hour, minute, 0, 0);
  
  // If target time has passed today, schedule for tomorrow
  if (target <= etTime) {
    target.setDate(target.getDate() + 1);
  }
  
  return target.getTime();
}


// =================================================================
// DOWNLOAD HANDLING (Downloads API) - SIMPLIFIED
// =================================================================

// 1. Listen for download creation
chrome.downloads.onCreated.addListener((downloadItem) => {
  console.log('📥 Download created:', downloadItem);
  
  // Check if this is our TradingView export
  if (downloadItem.url && downloadItem.url.includes('blob:') && 
      downloadItem.filename && downloadItem.filename.includes('.csv')) {
    
    console.log('🎯 TradingView CSV export detected. Adding to queue.');
    downloadQueue.set(downloadItem.id, {
      item: downloadItem,
      timestamp: Date.now(),
      type: 'tradingview_export'
    });
    
    // Show "saving" notification
    if (autoDownloadSettings.enableNotifications) {
        showDownloadNotification(downloadItem, 'saving');
    }
  }
});

// 2. Listen for filename request (THE MOST IMPORTANT PART)
// This is where we silently name and save the file.
chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
  console.log('📝 Determining filename for download:', downloadItem);
  
  // Check if it's our export
  if (downloadItem.url && downloadItem.url.includes('blob:') && 
      downloadItem.filename && downloadItem.filename.includes('.csv')) {
    
    console.log('🎯 Customizing filename for TradingView export');
    
    // Generate smart filename
    const timestamp = new Date().toISOString().replace(/:/g, '-').split('.')[0];
    
    // Use the symbol we stored from the content script
    let symbol = autoDownloadSettings.currentSymbol || 'UNKNOWN';
    symbol = symbol.replace(/[^a-zA-Z0-9!]/g, '_'); // Sanitize symbol
    
    const smartFilename = `${autoDownloadSettings.filePrefix}${symbol}_${timestamp}.csv`;
    const downloadPath = `${autoDownloadSettings.downloadPath}/${smartFilename}`;
    
    console.log(`📁 Smart filename: ${downloadPath}`);
    
    // Suggest the new path. This happens BEFORE the "Save As" dialog.
    suggest({
      filename: downloadPath,
      conflictAction: 'uniquify'
    });
    
    return true; // Indicates we are handling this asynchronously
  }
  
  // Not our export, let the browser handle it
  return false;
});


// 3. Monitor for completion or failure
chrome.downloads.onChanged.addListener((downloadDelta) => {
  // Check if this download is in our queue
  if (downloadQueue.has(downloadDelta.id)) {
    
    if (downloadDelta.state && downloadDelta.state.current === 'complete') {
      const download = downloadQueue.get(downloadDelta.id);
      console.log('✅ TradingView export completed:', download.item.filename);
      
      if (autoDownloadSettings.enableNotifications) {
        showDownloadNotification(download.item, 'completed');
      }
      
      // Clean up queue
      downloadQueue.delete(downloadDelta.id);
    }
    
    if (downloadDelta.state && downloadDelta.state.current === 'interrupted') {
      const download = downloadQueue.get(downloadDelta.id);
      console.log('❌ TradingView export failed:', downloadDelta.error);
      
      if (autoDownloadSettings.enableNotifications) {
        showDownloadNotification(download.item, 'failed', downloadDelta.error);
      }
      
      // Clean up queue
      downloadQueue.delete(downloadDelta.id);
    }
  }
});


// =================================================================
// MESSAGE LISTENER (Popup & Content Script)
// =================================================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received message:', request);
  
  if (request.action === 'updateAutoDownloadSettings') {
    autoDownloadSettings = { ...autoDownloadSettings, ...request.settings };
    console.log('✅ Auto-download settings updated:', autoDownloadSettings);
    sendResponse({success: true});
    return true;
  }
  
  // Handle symbol info updates from content script
  if (request.action === 'updateSymbolInfo') {
    console.log('📊 Received symbol info from content script:', request.symbol);
    
    // Store symbol info for smart filename generation
    autoDownloadSettings.currentSymbol = request.symbol;
    
    sendResponse({success: true});
    return true;
  }
  
  // Handle export request from popup (or alarm)
  if (request.action === 'exportWithDownloadsAPI' || request.action === 'exportData') {
    handleExportWithDownloadsAPI(request.settings)
      .then(result => sendResponse(result))
      .catch(error => sendResponse({success: false, error: error.message}));
    return true; // Keep message channel open
  }
  
  // Handle screenshot request
  if (request.action === 'captureTab') {
    captureCurrentTab()
      .then(() => sendResponse({success: true}))
      .catch(e => sendResponse({success: false, error: e.message}));
    return true;
  }
  
  // Other settings
  if (request.action === 'configureDownloads') {
    configureDownloadSettings(request.config);
    sendResponse({success: true});
    return true;
  }
});

/**
 * Main function to trigger an export
 * (Called by popup or alarm)
 */
async function handleExportWithDownloadsAPI(settings) {
  console.log('🚀 Handling export with Downloads API...');
  
  try {
    // Find active TradingView tab
    const tabs = await chrome.tabs.query({
      url: "*://www.tradingview.com/chart/*"
    });
    
    if (tabs.length === 0) {
      throw new Error('No TradingView chart tab found');
    }
    
    const tab = tabs[0];
    console.log('✅ Found TradingView tab:', tab.title);
    
    // Send export message to content script
    const result = await chrome.tabs.sendMessage(tab.id, {
      action: 'exportData',
      settings: settings || {}
    });
    
    if (result && result.success) {
      console.log('✅ Export initiated successfully by content script');
      return { success: true, message: 'Export started' };
    } else {
      throw new Error(result?.error || 'Export failed in content script');
    }
    
  } catch (error) {
    console.error('❌ Export with Downloads API failed:', error);
    return { success: false, error: error.message };
  }
}


// =================================================================
// HELPER FUNCTIONS
// =================================================================

/**
 * Show download notifications
 */
function showDownloadNotification(downloadItem, status, error = null) {
  let title, message;
  const iconUrl = 'icons/icon48.png';
  
  switch (status) {
    case 'saving':
      title = '💾 Saving TradingView Export';
      message = `Auto-saving: ${downloadItem.filename}`;
      break;
      
    case 'completed':
      title = '✅ Export Complete';
      message = `Successfully saved: ${downloadItem.filename}`;
      break;
      
    case 'failed':
      title = '❌ Export Failed';
      message = `Error: ${error || 'Unknown error'}`;
      break;
      
    case 'error':
      title = '⚠️ Processing Error';
      message = `Auto-save error: ${error || 'Unknown error'}`;
      break;
  }
  
  chrome.notifications.create(`export-${Date.now()}`, {
    type: 'basic',
    iconUrl: iconUrl,
    title: title,
    message: message
  });
}

/**
 * Configure download settings from popup
 */
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
      const filename = `tradingview_screenshot_${timestamp}.png`;
      
      chrome.downloads.download({
        url: dataUrl,
        filename: `tradingview_screenshots/${filename}`,
        saveAs: false
      });
      
      console.log('Screenshot saved:', filename);
    }
  } catch (error) {
    console.error('Failed to capture screenshot:', error);
  }
}

console.log('TradingView Exporter: Background ready');