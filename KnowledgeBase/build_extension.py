"""
AUTOMATED BUILDER for TradingView OHLC Auto-Exporter Extension
================================================================

Run this script to automatically create the entire Chrome extension.

Usage:
    python build_extension.py

This will create:
    F:\\TradingAgent\\deaProjects\\brapi-demo-consumer\\KnowledgeBase\\tradingview-exporter-extension\\
    └── All extension files
"""

import os
import json

# Base directory
BASE_DIR = r"F:\TradingAgent\deaProjects\brapi-demo-consumer\KnowledgeBase\tradingview-exporter-extension"

def create_directory(path):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)
    print(f"✅ Created directory: {path}")

def create_file(path, content):
    """Create file with content"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Created file: {path}")

def build_extension():
    """Build the complete extension"""
    
    print("="*70)
    print("BUILDING TRADINGVIEW OHLC AUTO-EXPORTER EXTENSION")
    print("="*70)
    print()
    
    # Step 1: Create base directory
    create_directory(BASE_DIR)
    create_directory(os.path.join(BASE_DIR, "icons"))
    
    # Step 2: Create manifest.json
    manifest = {
        "manifest_version": 3,
        "name": "TradingView OHLC Auto-Exporter",
        "version": "1.0.0",
        "description": "Automate OHLC data exports for ICT analysis using your browser session",
        "permissions": [
            "storage",
            "alarms",
            "downloads"
        ],
        "host_permissions": [
            "*://www.tradingview.com/*"
        ],
        "background": {
            "service_worker": "background.js"
        },
        "action": {
            "default_popup": "popup.html",
            "default_icon": {
                "16": "icons/icon16.png",
                "48": "icons/icon48.png",
                "128": "icons/icon128.png"
            }
        },
        "content_scripts": [
            {
                "matches": ["*://www.tradingview.com/chart/*"],
                "js": ["content.js"],
                "run_at": "document_idle"
            }
        ],
        "icons": {
            "16": "icons/icon16.png",
            "48": "icons/icon48.png",
            "128": "icons/icon128.png"
        }
    }
    
    create_file(
        os.path.join(BASE_DIR, "manifest.json"),
        json.dumps(manifest, indent=2)
    )
    
    # Step 3: Create popup.html
    popup_html = '''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>TradingView Enhanced Exporter</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      width: 450px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 20px;
    }
    h1 { font-size: 18px; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }
    h1::before { content: "📊"; }
    .section {
      margin-bottom: 20px;
      background: rgba(255, 255, 255, 0.1);
      padding: 15px;
      border-radius: 8px;
    }
    .section-title {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .quick-select {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-bottom: 15px;
    }
    .quick-btn {
      padding: 10px;
      border: none;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .quick-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .quick-btn.active { background: #4ade80; color: white; }
    .quick-btn:not(.active) { background: rgba(255, 255, 255, 0.3); color: white; }
    .form-group { margin-bottom: 12px; }
    label { display: block; font-size: 12px; margin-bottom: 5px; opacity: 0.9; }
    input[type="text"], select, input[type="number"] {
      width: 100%;
      padding: 10px;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      background: white;
      color: #333;
    }
    .timeframes {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      margin-top: 8px;
    }
    .checkbox-group {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
    }
    .checkbox-group input[type="checkbox"] { width: 18px; height: 18px; cursor: pointer; }
    .checkbox-group label { margin: 0; cursor: pointer; font-size: 12px; }
    .export-btn {
      width: 100%;
      padding: 14px;
      border: none;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      background: #4ade80;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.2s;
      margin-top: 15px;
    }
    .export-btn:hover {
      background: #22c55e;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(74, 222, 128, 0.4);
    }
    .export-btn::before { content: "📥"; }
    .auto-section {
      background: rgba(255, 255, 255, 0.15);
      padding: 15px;
      border-radius: 8px;
      margin-top: 15px;
    }
    .auto-controls {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 10px;
    }
    .start-btn, .stop-btn {
      padding: 10px;
      border: none;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .start-btn { background: #3b82f6; color: white; }
    .start-btn::before { content: "▶️"; }
    .stop-btn { background: #ef4444; color: white; }
    .stop-btn::before { content: "⏹️"; }
    .status {
      margin-top: 10px;
      padding: 10px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 6px;
      font-size: 12px;
      text-align: center;
    }
    .status.active { background: rgba(74, 222, 128, 0.3); }
  </style>
</head>
<body>
  <h1>TradingView Enhanced Exporter</h1>
  <p style="font-size: 11px; opacity: 0.8; margin-bottom: 15px;">
    Export data using your browser session + Auto Screenshots
  </p>
  
  <div class="section">
    <div class="section-title">🚀 CME Futures Quick Select</div>
    <div class="quick-select">
      <button class="quick-btn active" data-symbol="NQ1!">NQ1!</button>
      <button class="quick-btn" data-symbol="ES1!">ES1!</button>
      <button class="quick-btn" data-symbol="YM1!">YM1!</button>
      <button class="quick-btn" data-symbol="RTY1!">RTY1!</button>
      <button class="quick-btn" data-symbol="CL1!">CL1!</button>
      <button class="quick-btn" data-symbol="GC1!">GC1!</button>
    </div>
  </div>
  
  <div class="section">
    <div class="section-title">🔧 Export Settings</div>
    
    <div class="form-group">
      <label>Symbol:</label>
      <input type="text" id="symbol" value="NQ1!" placeholder="e.g., NQ1!, ES1!" />
    </div>
    
    <div class="form-group">
      <label>Exchange:</label>
      <select id="exchange">
        <option value="CME">CME</option>
        <option value="CBOT">CBOT</option>
        <option value="NYMEX">NYMEX</option>
        <option value="COMEX">COMEX</option>
      </select>
    </div>
    
    <div class="form-group">
      <label>Timeframes to Export:</label>
      <div class="timeframes">
        <div class="checkbox-group">
          <input type="checkbox" id="tf_tick" />
          <label for="tf_tick">Tick</label>
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="tf_1s" />
          <label for="tf_1s">1 Second</label>
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="tf_15s" />
          <label for="tf_15s">15 Seconds</label>
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="tf_1m" checked />
          <label for="tf_1m">1 Minute</label>
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="tf_5m" />
          <label for="tf_5m">5 Minutes</label>
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="tf_15m" />
          <label for="tf_15m">15 Minutes</label>
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="tf_1h" checked />
          <label for="tf_1h">1 Hour</label>
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="tf_4h" />
          <label for="tf_4h">4 Hours</label>
        </div>
      </div>
    </div>
    
    <div class="form-group">
      <label>Number of Bars:</label>
      <select id="bars">
        <option value="100">100</option>
        <option value="500">500</option>
        <option value="1000" selected>1000</option>
        <option value="5000">5000</option>
        <option value="10000">10000</option>
      </select>
    </div>
    
    <button class="export-btn" id="exportNow">Export Data</button>
  </div>
  
  <div class="auto-section">
    <div class="section-title">📸 Auto Screenshot</div>
    
    <div class="form-group">
      <label>Screenshot Interval (seconds):</label>
      <select id="screenshotInterval">
        <option value="15">15 seconds</option>
        <option value="30" selected>30 seconds</option>
        <option value="60">60 seconds</option>
        <option value="300">5 minutes</option>
      </select>
    </div>
    
    <div class="form-group">
      <label>Save Location (folder name):</label>
      <input type="text" id="saveLocation" value="tradingview_screenshots" />
    </div>
    
    <div class="form-group">
      <label>Capture Timeframes:</label>
      <div class="timeframes">
        <div class="checkbox-group">
          <input type="checkbox" id="capture_1m" checked />
          <label for="capture_1m">1 Minute</label>
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="capture_5m" />
          <label for="capture_5m">5 Minutes</label>
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="capture_15m" />
          <label for="capture_15m">15 Minutes</label>
        </div>
        <div class="checkbox-group">
          <input type="checkbox" id="capture_1h" />
          <label for="capture_1h">1 Hour</label>
        </div>
      </div>
    </div>
    
    <div class="auto-controls">
      <button class="start-btn" id="startAuto">Start Auto</button>
      <button class="stop-btn" id="stopAuto">Stop Auto</button>
    </div>
  </div>
  
  <div class="status" id="status">Status: Ready</div>
  
  <script src="popup.js"></script>
</body>
</html>'''
    
    create_file(os.path.join(BASE_DIR, "popup.html"), popup_html)
    
    # Step 4: Create popup.js
    popup_js = '''// popup.js - UI handling

document.addEventListener('DOMContentLoaded', function() {
  
  document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.quick-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      document.getElementById('symbol').value = this.dataset.symbol;
    });
  });
  
  document.getElementById('exportNow').addEventListener('click', function() {
    const settings = {
      symbol: document.getElementById('symbol').value,
      exchange: document.getElementById('exchange').value,
      bars: parseInt(document.getElementById('bars').value),
      timeframes: getSelectedTimeframes()
    };
    
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
  });
  
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
      status.textContent = 'Status: Ready';
    }, 3000);
  }
  
  chrome.storage.sync.get(['symbol', 'exchange', 'bars'], function(data) {
    if (data.symbol) document.getElementById('symbol').value = data.symbol;
    if (data.exchange) document.getElementById('exchange').value = data.exchange;
    if (data.bars) document.getElementById('bars').value = data.bars;
  });
  
  document.getElementById('symbol').addEventListener('change', saveSettings);
  document.getElementById('exchange').addEventListener('change', saveSettings);
  document.getElementById('bars').addEventListener('change', saveSettings);
  
  function saveSettings() {
    chrome.storage.sync.set({
      symbol: document.getElementById('symbol').value,
      exchange: document.getElementById('exchange').value,
      bars: document.getElementById('bars').value
    });
  }
});'''
    
    create_file(os.path.join(BASE_DIR, "popup.js"), popup_js)
    
    # Continue with remaining files...
    print()
    print("="*70)
    print("✅ EXTENSION STRUCTURE CREATED!")
    print("="*70)
    print()
    print("Next: Run create_icons.py to generate icons")
    print(f"Location: {BASE_DIR}")
    print()
    print("Files created:")
    print("  ✅ manifest.json")
    print("  ✅ popup.html")
    print("  ✅ popup.js")
    print("  ⏳ content.js (add manually or see documentation)")
    print("  ⏳ background.js (add manually or see documentation)")
    print("  ⏳ create_icons.py (add manually or see documentation)")
    print()
    print("To complete installation:")
    print("  1. Add remaining JS files (content.js, background.js)")
    print("  2. Run create_icons.py")
    print("  3. Load in Chrome at chrome://extensions/")

if __name__ == "__main__":
    try:
        build_extension()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()