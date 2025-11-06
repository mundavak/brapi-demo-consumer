// popup.js - Enhanced UI handling with Downloads API

document.addEventListener('DOMContentLoaded', function() {
  
  // Load saved download settings
  loadDownloadSettings();
  
  // Quick symbol selection
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.quick-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      document.getElementById('symbol').value = this.dataset.symbol;
    });
  });
  
  // Enhanced export with Downloads API
  document.getElementById('exportNow').addEventListener('click', function() {
    const settings = {
      symbol: document.getElementById('symbol').value,
      exchange: document.getElementById('exchange').value,
      timeframes: getSelectedTimeframes()
    };
    
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
          updateStatus('✅ Export started with Downloads API!');
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
  
  // Save download settings when changed
  document.getElementById('autoSaveEnabled').addEventListener('change', saveDownloadSettings);
  document.getElementById('downloadPath').addEventListener('input', saveDownloadSettings);
  document.getElementById('filePrefix').addEventListener('input', saveDownloadSettings);
  document.getElementById('enableNotifications').addEventListener('change', saveDownloadSettings);
  
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
      'tf_15s': '15s',
      'tf_1m': '1',
      'tf_5m': '5',
      'tf_15m': '15',
      'tf_1h': '60',
      'tf_4h': '240'
    };
    
    for (const [id, value] of Object.entries(checkboxes)) {
      if (document.getElementById(id).checked) {
        timeframes.push(value);
      }
    }
    
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
    
    setTimeout(() => {
      status.textContent = 'Ready';
    }, 3000);
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
      document.getElementById('autoSaveEnabled').checked = result.autoSaveEnabled !== false; // Default true
      document.getElementById('downloadPath').value = result.downloadPath || 'TradingView_Data';
      document.getElementById('filePrefix').value = result.filePrefix || 'chart_export_';
      document.getElementById('enableNotifications').checked = result.enableNotifications !== false; // Default true
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