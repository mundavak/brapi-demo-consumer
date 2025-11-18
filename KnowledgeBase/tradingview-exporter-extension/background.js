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
  currentSymbol: 'UNKNOWN', // Stores symbol from content script
  currentTimeframe: '1m'    // Stores timeframe from content script
};

// Scheduler settings
let schedulerSettings = {
  enabled: false,
  times: ['08:00'],
  timeframes: ['1', '60'],
  nextExport: null
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
  
  // Handle custom scheduler alarms
  if (alarm.name.startsWith('scheduler_export_')) {
    console.log('⏰ Custom scheduler alarm triggered:', alarm.name);
    handleScheduledExport();
  }
});


// 2. Create the alarm when the extension is installed or updated
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed/updated. Setting up daily alarm...');
  createDailyAlarm();
  loadSchedulerSettings();
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
// CUSTOM SCHEDULER FUNCTIONS
// =================================================================

/**
 * Load scheduler settings from storage
 */
function loadSchedulerSettings() {
  chrome.storage.sync.get([
    'schedulerEnabled',
    'schedulerTimes', 
    'autoExportTimeframes'
  ], function(result) {
    if (result.schedulerEnabled) {
      schedulerSettings.enabled = result.schedulerEnabled;
      schedulerSettings.times = result.schedulerTimes || ['08:00'];
      schedulerSettings.timeframes = result.autoExportTimeframes || ['1', '60'];
      
      if (schedulerSettings.enabled) {
        setupSchedulerAlarms();
      }
    }
  });
}

/**
 * Setup alarms for scheduler times
 */
function setupSchedulerAlarms() {
  // Clear existing scheduler alarms
  chrome.alarms.getAll(function(alarms) {
    alarms.forEach(alarm => {
      if (alarm.name.startsWith('scheduler_export_')) {
        chrome.alarms.clear(alarm.name);
      }
    });
    
    // Create new alarms for each time
    schedulerSettings.times.forEach(time => {
      const [hours, minutes] = time.split(':').map(Number);
      const nextAlarm = getNextExportTime(hours, minutes);
      
      const alarmName = `scheduler_export_${time.replace(':', '')}`;
      
      chrome.alarms.create(alarmName, {
        when: nextAlarm,
        periodInMinutes: 24 * 60 // Repeat daily
      });
      
      console.log(`⏰ Created scheduler alarm: ${alarmName} at ${new Date(nextAlarm).toLocaleString()}`);
    });
    
    // Update next export time
    updateNextExportTime();
  });
}

/**
 * Handle scheduled export
 */
async function handleScheduledExport() {
  console.log('🔄 Starting scheduled export...');
  
  if (!schedulerSettings.enabled || schedulerSettings.timeframes.length === 0) {
    console.log('⏰ Scheduler disabled or no timeframes selected');
    return;
  }
  
  try {
    // Find active TradingView tab
    const tabs = await chrome.tabs.query({
      url: "*://www.tradingview.com/chart/*"
    });
    
    if (tabs.length === 0) {
      console.log('❌ No TradingView chart tab found for scheduled export');
      return;
    }
    
    const tab = tabs[0];
    console.log('✅ Found TradingView tab for scheduled export:', tab.title);
    
    // Send export message to content script with scheduler timeframes
    const result = await chrome.tabs.sendMessage(tab.id, {
      action: 'exportData',
      settings: {
        timeframes: schedulerSettings.timeframes,
        isScheduled: true
      }
    });
    
    if (result && result.success) {
      console.log('✅ Scheduled export initiated successfully');
      
      // Show notification
      if (autoDownloadSettings.enableNotifications) {
        chrome.notifications.create(`scheduled-export-${Date.now()}`, {
          type: 'basic',
          iconUrl: 'icons/icon48.png',
          title: '⏰ Scheduled Export Started',
          message: `Exporting ${schedulerSettings.timeframes.length} timeframe(s)`
        });
      }
    } else {
      throw new Error(result?.error || 'Scheduled export failed in content script');
    }
    
  } catch (error) {
    console.error('❌ Scheduled export failed:', error);
    
    if (autoDownloadSettings.enableNotifications) {
      chrome.notifications.create(`scheduled-export-error-${Date.now()}`, {
        type: 'basic',
        iconUrl: 'icons/icon48.png',
        title: '❌ Scheduled Export Failed',
        message: error.message
      });
    }
  }
}

/**
 * Update next export time display
 */
function updateNextExportTime() {
  if (schedulerSettings.times.length === 0) {
    schedulerSettings.nextExport = 'No times set';
    return;
  }
  
  // Find the next upcoming time
  const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
  let nextTime = null;
  
  schedulerSettings.times.forEach(time => {
    const [hours, minutes] = time.split(':').map(Number);
    const candidate = new Date(now);
    candidate.setHours(hours, minutes, 0, 0);
    
    if (candidate <= now) {
      candidate.setDate(candidate.getDate() + 1);
    }
    
    if (!nextTime || candidate < nextTime) {
      nextTime = candidate;
    }
  });
  
  if (nextTime) {
    schedulerSettings.nextExport = nextTime.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      timeZone: 'America/New_York'
    });
  }
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
      type: 'tradingview_export',
      symbol: autoDownloadSettings.currentSymbol,
      timeframe: autoDownloadSettings.currentTimeframe
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
    
    // Generate smart filename with symbol and timeframe
    const timestamp = new Date().toISOString().replace(/:/g, '-').split('.')[0];
    
    // Use the symbol and timeframe we stored from the content script
    let symbol = autoDownloadSettings.currentSymbol || 'UNKNOWN';
    let timeframe = autoDownloadSettings.currentTimeframe || '1m';
    
    symbol = symbol.replace(/[^a-zA-Z0-9!]/g, '_'); // Sanitize symbol
    
    // Convert timeframe code to readable format
    const timeframeMap = {
      'tick': 'tick',
      '1s': '1s',
      '1': '1m',
      '5': '5m',
      '15': '15m',
      '30': '30m',
      '60': '1h',
      '120': '2h',
      '240': '4h',
      '1D': '1D'
    };
    
    const readableTimeframe = timeframeMap[timeframe] || timeframe;
    
    // Determine folder based on export type
    const folder = downloadQueue.get(downloadItem.id)?.type === 'scheduled_export' 
      ? `${autoDownloadSettings.downloadPath}/Auto_Exports`
      : autoDownloadSettings.downloadPath;
    
    // NEW: Create filename with symbol and timeframe
    const smartFilename = `${symbol}_${readableTimeframe}_${timestamp}.csv`;
    const downloadPath = `${folder}/${smartFilename}`;
    
    console.log(`📁 Smart filename: ${downloadPath}`);
    console.log(`   Symbol: ${symbol}`);
    console.log(`   Timeframe: ${readableTimeframe} (code: ${timeframe})`);
    
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
    console.log('📊 Received symbol info from content script:', request.symbol, request.timeframe);
    
    // Store symbol and timeframe info for smart filename generation
    autoDownloadSettings.currentSymbol = request.symbol;
    autoDownloadSettings.currentTimeframe = request.timeframe || '1m';
    
    console.log(`📝 Updated export info - Symbol: ${autoDownloadSettings.currentSymbol}, Timeframe: ${autoDownloadSettings.currentTimeframe}`);
    
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
  
  // Handle scheduler requests
  if (request.action === 'startScheduler') {
    schedulerSettings = {
      enabled: true,
      times: request.settings.schedulerTimes,
      timeframes: request.settings.autoExportTimeframes
    };
    
    setupSchedulerAlarms();
    
    // Save to storage
    chrome.storage.sync.set({
      schedulerEnabled: true,
      schedulerTimes: schedulerSettings.times,
      autoExportTimeframes: schedulerSettings.timeframes
    });
    
    sendResponse({success: true});
    return true;
  }
  
  if (request.action === 'stopScheduler') {
    schedulerSettings.enabled = false;
    
    // Clear scheduler alarms
    chrome.alarms.getAll(function(alarms) {
      alarms.forEach(alarm => {
        if (alarm.name.startsWith('scheduler_export_')) {
          chrome.alarms.clear(alarm.name);
        }
      });
    });
    
    // Save to storage
    chrome.storage.sync.set({
      schedulerEnabled: false
    });
    
    sendResponse({success: true});
    return true;
  }
  
  if (request.action === 'getSchedulerStatus') {
    updateNextExportTime();
    sendResponse({
      active: schedulerSettings.enabled,
      nextExport: schedulerSettings.nextExport
    });
    return true;
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