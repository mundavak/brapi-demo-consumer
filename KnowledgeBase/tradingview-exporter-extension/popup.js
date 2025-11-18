// popup.js - Enhanced UI handling with Downloads API & Timeframe Support

document.addEventListener('DOMContentLoaded', function() {
  
  // Load saved download settings
  loadDownloadSettings();
  
  // Load scheduler settings
  loadSchedulerSettings();
  
  // Quick symbol selection
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.quick-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      document.getElementById('symbol').value = this.dataset.symbol;
    });
  });
  
  // Enhanced export with Downloads API and Timeframe Support
  document.getElementById('exportNow').addEventListener('click', function() {
    const settings = {
      symbol: document.getElementById('symbol').value,
      exchange: document.getElementById('exchange').value,
      timeframes: getSelectedTimeframes()
    };
    
    console.log('🚀 Export settings with timeframes:', settings);
    
    // Validate at least one timeframe is selected
    if (settings.timeframes.length === 0) {
      updateStatus('⚠️ Please select at least one timeframe!');
      return;
    }
    
    // Save download settings to background
    saveDownloadSettings();
    
    // Use Downloads API if available
    if (chrome.downloads) {
      console.log('🚀 Using Downloads API for enhanced export...');
      
      chrome.runtime.sendMessage({
        action: 'exportWithDownloadsAPI',
        settings: settings
      }, function(response) {
        if (response && response.success) {
          updateStatus(`✅ Export started for ${settings.timeframes.length} timeframe(s)!`);
        } else {
          updateStatus('❌ Error: ' + (response?.error || 'Unknown error'));
          fallbackToBasicExport(settings);
        }
      });
    } else {
      // Fallback to basic export
      fallbackToBasicExport(settings);
    }
  });
  
  // Quick timeframe selection buttons
  setupQuickTimeframeButtons();
  
  // Save download settings when changed
  document.getElementById('autoSaveEnabled').addEventListener('change', saveDownloadSettings);
  document.getElementById('downloadPath').addEventListener('input', saveDownloadSettings);
  document.getElementById('filePrefix').addEventListener('input', saveDownloadSettings);
  document.getElementById('enableNotifications').addEventListener('change', saveDownloadSettings);
  
  // Timeframe checkboxes event listeners
  setupTimeframeCheckboxes();
  
  // NEW: Auto Export Scheduler functionality
  setupScheduler();
  
  document.getElementById('startAuto').addEventListener('click', function() {
    const settings = {
      interval: parseInt(document.getElementById('screenshotInterval').value),
      saveLocation: document.getElementById('saveLocation').value,
      captureTimeframes: getCaptureTimeframes()
    };
    
    chrome.runtime.sendMessage({
      action: 'startAuto',
      settings: settings
    }, function(response) {
      updateStatus('Auto-screenshot started!');
      document.querySelector('.status').classList.add('active');
    });
  });
  
  document.getElementById('stopAuto').addEventListener('click', function() {
    chrome.runtime.sendMessage({
      action: 'stopAuto'
    }, function(response) {
      updateStatus('Auto-screenshot stopped');
      document.querySelector('.status').classList.remove('active');
    });
  });
  
  // Monitor controls
  document.getElementById('startMonitor').addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (tabs[0] && tabs[0].url.includes('tradingview.com')) {
        chrome.tabs.sendMessage(tabs[0].id, {
          action: 'startMonitoring'
        }, function(response) {
          if (chrome.runtime.lastError) {
            updateStatus('Error: ' + chrome.runtime.lastError.message);
          } else {
            updateStatus('Monitoring started - perform export manually');
            document.querySelector('.status').classList.add('active');
          }
        });
      } else {
        updateStatus('Please open TradingView chart first!');
      }
    });
  });
  
  document.getElementById('stopMonitor').addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (tabs[0] && tabs[0].url.includes('tradingview.com')) {
        chrome.tabs.sendMessage(tabs[0].id, {
          action: 'stopMonitoring'
        }, function(response) {
          if (chrome.runtime.lastError) {
            updateStatus('Error: ' + chrome.runtime.lastError.message);
          } else {
            updateStatus('Monitoring stopped - check Downloads folder');
            document.querySelector('.status').classList.remove('active');
          }
        });
      }
    });
  });
  
  document.getElementById('getReport').addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (tabs[0] && tabs[0].url.includes('tradingview.com')) {
        chrome.tabs.sendMessage(tabs[0].id, {
          action: 'getReport'
        }, function(response) {
          if (chrome.runtime.lastError) {
            updateStatus('Error: ' + chrome.runtime.lastError.message);
          } else if (response && response.success) {
            updateStatus('Report downloaded to Downloads folder!');
          } else {
            updateStatus('No monitoring data available - start monitor first');
          }
        });
      }
    });
  });
  
  function getSelectedTimeframes() {
    const timeframes = [];
    const checkboxes = {
      'tf_tick': 'tick',
      'tf_1s': '1s',
      'tf_1m': '1',
      'tf_5m': '5',
      'tf_15m': '15',
      'tf_30m': '30',
      'tf_1h': '60',
      'tf_2h': '120',
      'tf_4h': '240',
      'tf_1D': '1D'
    };
    
    for (const [id, value] of Object.entries(checkboxes)) {
      if (document.getElementById(id).checked) {
        timeframes.push(value);
      }
    }
    
    console.log('Selected timeframes:', timeframes);
    return timeframes;
  }
  
  function getCaptureTimeframes() {
    const timeframes = [];
    const checkboxes = {
      'capture_1m': '1',
      'capture_5m': '5',
      'capture_15m': '15',
      'capture_1h': '60'
    };
    
    for (const [id, value] of Object.entries(checkboxes)) {
      if (document.getElementById(id).checked) {
        timeframes.push(value);
      }
    }
    
    return timeframes;
  }
  
  function updateStatus(message) {
    const status = document.getElementById('status');
    status.textContent = `Status: ${message}`;
    status.className = 'status'; // Reset classes
    
    // Add appropriate class based on message
    if (message.includes('✅')) status.classList.add('success');
    else if (message.includes('❌') || message.includes('Error')) status.classList.add('error');
    else if (message.includes('⚠️')) status.classList.add('warning');
    
    setTimeout(() => {
      status.textContent = 'Ready';
      status.className = 'status';
    }, 5000);
  }
  
  // Downloads API Settings Management
  function loadDownloadSettings() {
    console.log('📁 Loading download settings...');
    
    chrome.storage.sync.get([
      'autoSaveEnabled',
      'downloadPath', 
      'filePrefix',
      'enableNotifications'
    ], function(result) {
      console.log('💾 Loaded settings:', result);
      
      // Set UI values
      document.getElementById('autoSaveEnabled').checked = result.autoSaveEnabled !== false;
      document.getElementById('downloadPath').value = result.downloadPath || 'TradingView_Data';
      document.getElementById('filePrefix').value = result.filePrefix || 'chart_export_';
      document.getElementById('enableNotifications').checked = result.enableNotifications !== false;
    });
  }
  
  function saveDownloadSettings() {
    const settings = {
      autoSaveEnabled: document.getElementById('autoSaveEnabled').checked,
      downloadPath: document.getElementById('downloadPath').value,
      filePrefix: document.getElementById('filePrefix').value,
      enableNotifications: document.getElementById('enableNotifications').checked
    };
    
    console.log('💾 Saving download settings:', settings);
    
    // Save to storage
    chrome.storage.sync.set(settings, function() {
      console.log('✅ Download settings saved');
    });
    
    // Send to background script
    chrome.runtime.sendMessage({
      action: 'updateAutoDownloadSettings',
      settings: settings
    });
  }
  
  function fallbackToBasicExport(settings) {
    console.log('⬇️ Falling back to basic export...');
    
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (tabs[0] && tabs[0].url.includes('tradingview.com')) {
        chrome.tabs.sendMessage(tabs[0].id, {
          action: 'export',
          settings: settings
        }, function(response) {
          updateStatus(response ? response.message : 'Export started...');
        });
      } else {
        updateStatus('Please open TradingView chart first!');
      }
    });
  }
  
  // Setup quick timeframe selection buttons
  function setupQuickTimeframeButtons() {
    const quickTimeframes = {
      'quickAll': ['tick', '1s', '1', '5', '15', '30', '60', '120', '240', '1D'],
      'quickMinutes': ['1', '5', '15'],
      'quickHours': ['60', '120', '240'],
      'quickSeconds': ['tick', '1s']
    };
    
    for (const [buttonId, timeframes] of Object.entries(quickTimeframes)) {
      const button = document.getElementById(buttonId);
      if (button) {
        button.addEventListener('click', function() {
          // Clear all timeframe checkboxes first
          const allTimeframeCheckboxes = document.querySelectorAll('input[id^="tf_"]');
          allTimeframeCheckboxes.forEach(checkbox => {
            checkbox.checked = false;
          });
          
          // Select the specified timeframes
          timeframes.forEach(tf => {
            const checkboxId = getCheckboxIdForTimeframe(tf);
            const checkbox = document.getElementById(checkboxId);
            if (checkbox) {
              checkbox.checked = true;
            }
          });
          
          updateStatus(`✅ Selected ${timeframes.length} timeframes`);
        });
      }
    }
  }
  
  // Helper function to get checkbox ID for timeframe
  function getCheckboxIdForTimeframe(timeframe) {
    const mapping = {
      'tick': 'tf_tick',
      '1s': 'tf_1s',
      '1': 'tf_1m',
      '5': 'tf_5m',
      '15': 'tf_15m',
      '30': 'tf_30m',
      '60': 'tf_1h',
      '120': 'tf_2h',
      '240': 'tf_4h',
      '1D': 'tf_1D'
    };
    return mapping[timeframe];
  }
  
  // Setup timeframe checkbox change listeners
  function setupTimeframeCheckboxes() {
    const timeframeCheckboxes = document.querySelectorAll('input[id^="tf_"]');
    timeframeCheckboxes.forEach(checkbox => {
      checkbox.addEventListener('change', function() {
        const selectedCount = getSelectedTimeframes().length;
        
        // Update the export button text
        const exportButton = document.getElementById('exportNow');
        if (selectedCount > 0) {
          exportButton.textContent = `Export ${selectedCount} Timeframe(s)`;
        } else {
          exportButton.textContent = 'Export Visible Data';
        }
      });
    });
  }
  
  // NEW: Auto Export Scheduler Functions
  function setupScheduler() {
    // Add time button
    document.getElementById('addTime').addEventListener('click', addTimeInput);
    
    // Start/Stop scheduler buttons
    document.getElementById('startScheduler').addEventListener('click', startScheduler);
    document.getElementById('stopScheduler').addEventListener('click', stopScheduler);
    
    // Scheduler enabled checkbox
    document.getElementById('schedulerEnabled').addEventListener('change', saveSchedulerSettings);
    
    // Auto timeframe checkboxes
    const autoTimeframeCheckboxes = document.querySelectorAll('input[id^="auto_tf_"]');
    autoTimeframeCheckboxes.forEach(checkbox => {
      checkbox.addEventListener('change', saveSchedulerSettings);
    });
    
    // Remove time buttons
    document.addEventListener('click', function(e) {
      if (e.target.classList.contains('remove-time')) {
        e.target.parentElement.remove();
        saveSchedulerSettings();
      }
    });
    
    // Time input changes
    document.addEventListener('change', function(e) {
      if (e.target.classList.contains('export-time')) {
        saveSchedulerSettings();
      }
    });
    
    // Load current scheduler status
    updateSchedulerStatus();
  }
  
  function addTimeInput() {
    const timesContainer = document.getElementById('schedulerTimes');
    const timeInputGroup = document.createElement('div');
    timeInputGroup.className = 'time-input-group';
    timeInputGroup.innerHTML = `
      <input type="time" class="export-time" value="09:00" />
      <button class="remove-time">×</button>
    `;
    timesContainer.appendChild(timeInputGroup);
    saveSchedulerSettings();
  }
  
  function getSchedulerTimes() {
    const timeInputs = document.querySelectorAll('.export-time');
    const times = [];
    timeInputs.forEach(input => {
      if (input.value) {
        times.push(input.value);
      }
    });
    return times;
  }
  
  function getAutoExportTimeframes() {
    const timeframes = [];
    const checkboxes = {
      'auto_tf_1m': '1',
      'auto_tf_5m': '5',
      'auto_tf_15m': '15',
      'auto_tf_1h': '60',
      'auto_tf_4h': '240'
    };
    
    for (const [id, value] of Object.entries(checkboxes)) {
      if (document.getElementById(id).checked) {
        timeframes.push(value);
      }
    }
    
    return timeframes;
  }
  
  function loadSchedulerSettings() {
    chrome.storage.sync.get([
      'schedulerEnabled',
      'schedulerTimes',
      'autoExportTimeframes',
      'schedulerStatus'
    ], function(result) {
      console.log('⏰ Loaded scheduler settings:', result);
      
      // Set scheduler enabled
      document.getElementById('schedulerEnabled').checked = result.schedulerEnabled || false;
      
      // Set times
      const timesContainer = document.getElementById('schedulerTimes');
      timesContainer.innerHTML = '';
      
      const times = result.schedulerTimes || ['08:00'];
      times.forEach(time => {
        const timeInputGroup = document.createElement('div');
        timeInputGroup.className = 'time-input-group';
        timeInputGroup.innerHTML = `
          <input type="time" class="export-time" value="${time}" />
          <button class="remove-time">×</button>
        `;
        timesContainer.appendChild(timeInputGroup);
      });
      
      // Set auto export timeframes
      const autoTimeframes = result.autoExportTimeframes || ['1', '60'];
      const checkboxes = {
        '1': 'auto_tf_1m',
        '5': 'auto_tf_5m',
        '15': 'auto_tf_15m',
        '60': 'auto_tf_1h',
        '240': 'auto_tf_4h'
      };
      
      // Clear all first
      Object.values(checkboxes).forEach(id => {
        document.getElementById(id).checked = false;
      });
      
      // Set checked ones
      autoTimeframes.forEach(tf => {
        const checkboxId = checkboxes[tf];
        if (checkboxId) {
          document.getElementById(checkboxId).checked = true;
        }
      });
      
      updateSchedulerStatus();
    });
  }
  
  function saveSchedulerSettings() {
    const settings = {
      schedulerEnabled: document.getElementById('schedulerEnabled').checked,
      schedulerTimes: getSchedulerTimes(),
      autoExportTimeframes: getAutoExportTimeframes()
    };
    
    console.log('⏰ Saving scheduler settings:', settings);
    
    chrome.storage.sync.set(settings, function() {
      console.log('✅ Scheduler settings saved');
    });
  }
  
  function startScheduler() {
    const settings = {
      schedulerEnabled: true,
      schedulerTimes: getSchedulerTimes(),
      autoExportTimeframes: getAutoExportTimeframes()
    };
    
    if (settings.schedulerTimes.length === 0) {
      updateSchedulerStatus('❌ Please add at least one export time');
      return;
    }
    
    if (settings.autoExportTimeframes.length === 0) {
      updateSchedulerStatus('❌ Please select at least one timeframe for auto-export');
      return;
    }
    
    chrome.runtime.sendMessage({
      action: 'startScheduler',
      settings: settings
    }, function(response) {
      if (response && response.success) {
        updateSchedulerStatus('✅ Scheduler started successfully');
        document.getElementById('schedulerStatus').classList.add('active');
        document.getElementById('schedulerEnabled').checked = true;
        saveSchedulerSettings();
      } else {
        updateSchedulerStatus('❌ Failed to start scheduler: ' + (response?.error || 'Unknown error'));
      }
    });
  }
  
  function stopScheduler() {
    chrome.runtime.sendMessage({
      action: 'stopScheduler'
    }, function(response) {
      if (response && response.success) {
        updateSchedulerStatus('⏹️ Scheduler stopped');
        document.getElementById('schedulerStatus').classList.remove('active');
        document.getElementById('schedulerEnabled').checked = false;
        saveSchedulerSettings();
      } else {
        updateSchedulerStatus('❌ Failed to stop scheduler');
      }
    });
  }
  
  function updateSchedulerStatus(message) {
    const statusElement = document.getElementById('schedulerStatus');
    if (message) {
      statusElement.textContent = `Status: ${message}`;
    }
    
    // Check current scheduler status
    chrome.runtime.sendMessage({action: 'getSchedulerStatus'}, function(response) {
      if (response && response.active) {
        statusElement.textContent = `Status: ✅ Active - Next export at ${response.nextExport}`;
        statusElement.classList.add('active');
        document.getElementById('schedulerEnabled').checked = true;
      } else {
        if (!message) {
          statusElement.textContent = 'Status: Ready';
        }
        statusElement.classList.remove('active');
        document.getElementById('schedulerEnabled').checked = false;
      }
    });
  }
  
  // Load saved symbol and exchange
  chrome.storage.sync.get(['symbol', 'exchange'], function(data) {
    if (data.symbol) document.getElementById('symbol').value = data.symbol;
    if (data.exchange) document.getElementById('exchange').value = data.exchange;
  });
  
  document.getElementById('symbol').addEventListener('change', saveSettings);
  document.getElementById('exchange').addEventListener('change', saveSettings);
  
  function saveSettings() {
    chrome.storage.sync.set({
      symbol: document.getElementById('symbol').value,
      exchange: document.getElementById('exchange').value
    });
  }
});