// lightweight-monitor.js - Performance-optimized monitor
// Minimal DOM monitoring to avoid freezing

console.log('🔍 Lightweight Monitor: Loading...');

class LightweightMonitor {
  constructor() {
    this.isActive = false;
    this.events = [];
    this.maxEvents = 50; // Limit events to prevent memory issues
    
    this.init();
  }
  
  init() {
    this.createToggleButton();
    this.setupBasicListeners();
    console.log('✅ Lightweight Monitor: Ready');
  }
  
  createToggleButton() {
    // Check if button already exists to prevent duplicates
    if (document.getElementById('lightweight-monitor-btn')) {
      return;
    }
    
    const button = document.createElement('div');
    button.id = 'lightweight-monitor-btn';
    button.style.cssText = `
      position: fixed;
      top: 50px;
      right: 10px;
      z-index: 10001;
      background: #333;
      color: white;
      padding: 8px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-family: monospace;
      font-size: 11px;
      border: 1px solid #555;
    `;
    button.textContent = '🔍 Start Light Monitor';
    
    button.addEventListener('click', () => {
      this.toggle();
    });
    
    // Safely append to body
    try {
      if (document.body) {
        document.body.appendChild(button);
      } else {
        // Wait for body to be available
        document.addEventListener('DOMContentLoaded', () => {
          if (document.body) {
            document.body.appendChild(button);
          }
        });
      }
    } catch (error) {
      console.warn('Could not create monitor button:', error.message);
    }
  }
  
  toggle() {
    if (this.isActive) {
      this.stop();
    } else {
      this.start();
    }
  }
  
  start() {
    this.isActive = true;
    this.events = [];
    this.startTime = Date.now();
    
    const button = document.getElementById('lightweight-monitor-btn');
    if (button) {
      button.textContent = '⏹️ Stop Monitor';
      button.style.background = '#d32f2f';
    }
    
    console.log('🟢 Lightweight monitoring started');
    this.addEvent('Monitor started', 'info');
  }
  
  stop() {
    this.isActive = false;
    
    const button = document.getElementById('lightweight-monitor-btn');
    if (button) {
      button.textContent = '🔍 Start Light Monitor';
      button.style.background = '#333';
    }
    
    console.log('🔴 Lightweight monitoring stopped');
    this.addEvent('Monitor stopped', 'info');
    this.downloadReport();
  }
  
  setupBasicListeners() {
    // Only monitor essential events to avoid performance issues
    
    // Monitor context menu (right-click)
    document.addEventListener('contextmenu', (e) => {
      if (!this.isActive) return;
      this.addEvent(`Right-click on ${e.target.tagName}`, 'context');
    });
    
    // Monitor clicks on elements containing "export"
    document.addEventListener('click', (e) => {
      if (!this.isActive) return;
      
      const text = e.target.textContent?.toLowerCase();
      if (text && text.includes('export')) {
        this.addEvent(`Export click: "${e.target.textContent.trim()}"`, 'export');
        this.logElementDetails(e.target);
      }
    });
    
    // Simple DOM mutation observer (very limited scope)
    const observer = new MutationObserver((mutations) => {
      if (!this.isActive) return;
      
      // Only process 1 mutation per batch to avoid lag
      const mutation = mutations[0];
      if (mutation && mutation.type === 'childList') {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === 1 && node.textContent?.toLowerCase().includes('export')) {
            this.addEvent(`Export element added: ${node.tagName}`, 'export');
          }
        });
      }
    });
    
    // Only observe direct children of body (minimal scope)
    observer.observe(document.body, {
      childList: true,
      subtree: false
    });
  }
  
  addEvent(message, type) {
    const event = {
      timestamp: Date.now() - this.startTime,
      type,
      message,
      time: new Date().toLocaleTimeString()
    };
    
    this.events.push(event);
    
    // Limit events to prevent memory issues
    if (this.events.length > this.maxEvents) {
      this.events = this.events.slice(-this.maxEvents);
    }
    
    console.log(`[Light Monitor] ${message}`);
  }
  
  logElementDetails(element) {
    this.addEvent(`  Tag: ${element.tagName}`, 'detail');
    this.addEvent(`  Classes: ${element.className.substring(0, 30)}`, 'detail');
    this.addEvent(`  Text: "${element.textContent?.trim().substring(0, 30)}..."`, 'detail');
    
    const role = element.getAttribute('role');
    if (role) {
      this.addEvent(`  Role: ${role}`, 'detail');
    }
    
    const dataName = element.getAttribute('data-name');
    if (dataName) {
      this.addEvent(`  Data-name: ${dataName}`, 'detail');
    }
  }
  
  downloadReport() {
    const report = {
      session: `lightweight_${Date.now()}`,
      duration: this.startTime ? Date.now() - this.startTime : 0,
      totalEvents: this.events.length,
      events: this.events,
      summary: {
        exportEvents: this.events.filter(e => e.type === 'export').length,
        contextEvents: this.events.filter(e => e.type === 'context').length,
        detailEvents: this.events.filter(e => e.type === 'detail').length
      }
    };
    
    console.log('📊 Lightweight report data:', report);
    
    try {
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `lightweight-monitor-${Date.now()}.json`;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      console.log('� Lightweight report downloaded');
    } catch (error) {
      console.error('❌ Download failed:', error);
      
      // Fallback: log to console
      console.log('📋 REPORT DATA (copy this):', JSON.stringify(report, null, 2));
      
      // Try clipboard fallback
      try {
        navigator.clipboard.writeText(JSON.stringify(report, null, 2));
        console.log('📋 Report copied to clipboard');
      } catch (clipError) {
        console.warn('Clipboard also failed');
      }
    }
  }
}

// Initialize lightweight monitor safely
console.log('🔍 TradingView Monitor: Starting initialization...');

// Wait for DOM to be ready before initializing
function initializeLightMonitor() {
  try {
    const lightMonitor = new LightweightMonitor();
    window.lightMonitor = lightMonitor;
    console.log('✅ Lightweight Monitor loaded - minimal performance impact');
  } catch (error) {
    console.warn('Failed to initialize lightweight monitor:', error.message);
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeLightMonitor);
} else {
  // DOM is already ready
  initializeLightMonitor();
}