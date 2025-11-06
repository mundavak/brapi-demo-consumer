// TradingView DOM Monitor Extension
// Watches for DOM changes and user interactions to learn export workflow
// Based on MutationObserver and Event Listeners

console.log('🔍 TradingView Monitor: Loading...');

class TradingViewMonitor {
  constructor() {
    this.isMonitoring = false;
    this.observers = [];
    this.eventLogs = [];
    this.startTime = null;
    this.sessionId = this.generateSessionId();
    
    this.init();
  }
  
  generateSessionId() {
    return `monitor_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
  
  init() {
    console.log('🔍 TradingView Monitor: Initializing...');
    this.setupUI();
    this.attachGlobalListeners();
    console.log('✅ TradingView Monitor: Ready');
  }
  
  setupUI() {
    // Create monitoring control panel
    const panel = document.createElement('div');
    panel.id = 'tv-monitor-panel';
    panel.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      z-index: 10000;
      background: #1e1e1e;
      color: #fff;
      padding: 15px;
      border-radius: 8px;
      font-family: monospace;
      font-size: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      min-width: 300px;
      max-height: 400px;
      overflow-y: auto;
    `;
    
    panel.innerHTML = `
      <div style="margin-bottom: 10px;">
        <strong>🔍 TradingView Monitor</strong>
        <button id="tv-monitor-toggle" style="margin-left: 10px; padding: 5px 10px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer;">
          Start Monitoring
        </button>
        <button id="tv-monitor-clear" style="margin-left: 5px; padding: 5px 10px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer;">
          Clear
        </button>
      </div>
      <div id="tv-monitor-status" style="margin-bottom: 10px; color: #888;">
        Ready to monitor...
      </div>
      <div id="tv-monitor-log" style="max-height: 250px; overflow-y: auto; border-top: 1px solid #444; padding-top: 10px;">
      </div>
    `;
    
    document.body.appendChild(panel);
    
    // Attach button listeners
    document.getElementById('tv-monitor-toggle').addEventListener('click', () => {
      this.toggleMonitoring();
    });
    
    document.getElementById('tv-monitor-clear').addEventListener('click', () => {
      this.clearLog();
    });
    
    // Make panel draggable
    this.makeDraggable(panel);
  }
  
  makeDraggable(element) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    element.onmousedown = dragMouseDown;

    function dragMouseDown(e) {
      e = e || window.event;
      e.preventDefault();
      pos3 = e.clientX;
      pos4 = e.clientY;
      document.onmouseup = closeDragElement;
      document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
      e = e || window.event;
      e.preventDefault();
      pos1 = pos3 - e.clientX;
      pos2 = pos4 - e.clientY;
      pos3 = e.clientX;
      pos4 = e.clientY;
      element.style.top = (element.offsetTop - pos2) + "px";
      element.style.left = (element.offsetLeft - pos1) + "px";
    }

    function closeDragElement() {
      document.onmouseup = null;
      document.onmousemove = null;
    }
  }
  
  toggleMonitoring() {
    if (this.isMonitoring) {
      this.stopMonitoring();
    } else {
      this.startMonitoring();
    }
  }
  
  startMonitoring() {
    console.log('🔍 Starting TradingView monitoring...');
    this.isMonitoring = true;
    this.startTime = Date.now();
    this.eventLogs = [];
    
    // Update UI
    const toggleBtn = document.getElementById('tv-monitor-toggle');
    const statusDiv = document.getElementById('tv-monitor-status');
    
    if (toggleBtn) {
      toggleBtn.textContent = 'Stop Monitoring';
      toggleBtn.style.background = '#f44336';
    }
    
    if (statusDiv) {
      statusDiv.textContent = '🟢 MONITORING ACTIVE - Perform your export workflow manually...';
      statusDiv.style.color = '#4CAF50';
    }
    
    // Setup DOM mutation observers
    this.setupMutationObservers();
    
    // Setup enhanced event listeners
    this.setupEventListeners();
    
    this.log('🚀 Monitoring started', 'info');
    this.log('📋 Instructions: Right-click chart → Export chart data → Watch the magic!', 'info');
    
    // Add a test event to ensure system is working
    this.log('🧪 Test event - monitoring system is active', 'test');
  }
  
  stopMonitoring() {
    console.log('🔍 Stopping TradingView monitoring...');
    this.isMonitoring = false;
    
    // Update UI
    const toggleBtn = document.getElementById('tv-monitor-toggle');
    const statusDiv = document.getElementById('tv-monitor-status');
    
    toggleBtn.textContent = 'Start Monitoring';
    toggleBtn.style.background = '#2196F3';
    statusDiv.textContent = '🔴 MONITORING STOPPED';
    statusDiv.style.color = '#888';
    
    // Disconnect all observers
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
    
    this.log('🛑 Monitoring stopped', 'info');
    this.generateReport();
  }
  
  setupMutationObservers() {
    // Throttled configuration to prevent performance issues
    const configs = [
      {
        name: 'Body Changes',
        target: document.body,
        config: {
          childList: true,
          subtree: false, // Reduced scope to prevent recursion
          attributes: false,
          characterData: false
        }
      }
    ];
    
    // Throttle mutation handling to prevent flooding
    let mutationQueue = [];
    let processTimeout = null;
    
    const processMutations = () => {
      if (mutationQueue.length > 0) {
        // Process only recent mutations to avoid lag
        const recentMutations = mutationQueue.slice(-10);
        mutationQueue = [];
        
        recentMutations.forEach(({mutations, observerName}) => {
          this.handleMutationsThrottled(mutations, observerName);
        });
      }
      processTimeout = null;
    };
    
    configs.forEach(({name, target, config}) => {
      const observer = new MutationObserver((mutations) => {
        if (!this.isMonitoring) return;
        
        // Queue mutations instead of processing immediately
        mutationQueue.push({mutations, observerName: name});
        
        // Throttle processing to every 500ms
        if (!processTimeout) {
          processTimeout = setTimeout(processMutations, 500);
        }
      });
      
      observer.observe(target, config);
      this.observers.push(observer);
    });
  }
  
  handleMutationsThrottled(mutations, observerName) {
    if (!this.isMonitoring) return;
    
    // Limit mutations processed to prevent freezing
    const limitedMutations = mutations.slice(0, 5);
    
    limitedMutations.forEach(mutation => {
      const timestamp = Date.now() - this.startTime;
      
      if (mutation.type === 'childList') {
        // Only check added nodes that might be menus/dialogs
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE && this.isRelevantElement(node)) {
            this.analyzeAddedElementSafe(node, timestamp);
          }
        });
      }
    });
  }
  
  isRelevantElement(element) {
    if (!element.textContent) return false;
    
    const text = element.textContent.toLowerCase();
    const role = element.getAttribute('role');
    const classes = element.className || '';
    
    // Only monitor export-related, menu, or dialog elements
    return (
      text.includes('export') ||
      role === 'menu' ||
      role === 'dialog' ||
      role === 'menuitem' ||
      classes.includes('menu') ||
      classes.includes('dialog')
    );
  }
  
  analyzeAddedElementSafe(element, timestamp) {
    try {
      const text = element.textContent?.trim().toLowerCase();
      const classes = element.className;
      const role = element.getAttribute('role');
      
      // Check for export-related elements
      if (text && text.includes('export')) {
        this.log(`➕ Export element: "${element.textContent?.trim().substring(0, 30)}..." (${element.tagName})`, 'export', timestamp);
      }
      
      // Check for menu elements
      if (role === 'menu' || role === 'menuitem' || classes.includes('menu')) {
        this.log(`🎯 Menu element: ${element.tagName} (role: ${role})`, 'menu', timestamp);
        this.analyzeMenuContentSafe(element, timestamp);
      }
      
      // Check for dialog elements
      if (role === 'dialog' || classes.includes('dialog')) {
        this.log(`💬 Dialog element added`, 'dialog', timestamp);
        this.analyzeDialogContentSafe(element, timestamp);
      }
    } catch (error) {
      // Silently handle errors to prevent crashes
      console.warn('Monitor error:', error.message);
    }
  }
  
  analyzeAddedElement(element, timestamp) {
    const text = element.textContent?.trim().toLowerCase();
    const classes = element.className;
    const role = element.getAttribute('role');
    
    // Check for export-related elements
    if (text && text.includes('export')) {
      this.log(`➕ Export element added: "${element.textContent?.trim()}" (${element.tagName})`, 'export', timestamp);
      this.log(`   Classes: ${classes}`, 'detail', timestamp);
      this.log(`   Role: ${role || 'none'}`, 'detail', timestamp);
      this.logElementStructure(element, timestamp);
    }
    
    // Check for menu elements
    if (role === 'menu' || role === 'menuitem' || classes.includes('menu')) {
      this.log(`🎯 Menu element added: ${element.tagName} (role: ${role})`, 'menu', timestamp);
      this.analyzeMenuContent(element, timestamp);
    }
    
    // Check for dialog elements
    if (role === 'dialog' || classes.includes('dialog') || text.includes('export chart data')) {
      this.log(`💬 Dialog element added: "${text.substring(0, 50)}..."`, 'dialog', timestamp);
      this.analyzeDialogContent(element, timestamp);
    }
  }
  
  analyzeRemovedElement(element, timestamp) {
    const text = element.textContent?.trim();
    if (text && text.toLowerCase().includes('export')) {
      this.log(`➖ Export element removed: "${text.substring(0, 30)}..."`, 'export', timestamp);
    }
  }
  
  analyzeAttributeChange(mutation, timestamp) {
    const element = mutation.target;
    const attrName = mutation.attributeName;
    const oldValue = mutation.oldValue;
    const newValue = element.getAttribute(attrName);
    
    // Log significant attribute changes
    if (['class', 'style', 'aria-label'].includes(attrName) && oldValue !== newValue) {
      const text = element.textContent?.trim();
      if (text && text.toLowerCase().includes('export')) {
        this.log(`🔄 Export element attribute changed: ${attrName}`, 'attr', timestamp);
        this.log(`   Old: ${oldValue}`, 'detail', timestamp);
        this.log(`   New: ${newValue}`, 'detail', timestamp);
      }
    }
  }
  
  analyzeMenuContentSafe(menuElement, timestamp) {
    try {
      const items = menuElement.querySelectorAll('[role="menuitem"], .menu-item, [class*="item"]');
      this.log(`   📋 Menu contains ${Math.min(items.length, 10)} items`, 'detail', timestamp);
      
      // Limit to first 5 items to prevent lag
      const limitedItems = Array.from(items).slice(0, 5);
      
      limitedItems.forEach((item, index) => {
        const text = item.textContent?.trim();
        if (text && text.length < 100) { // Avoid very long text
          if (text.toLowerCase().includes('export')) {
            this.log(`     🎯 EXPORT ITEM FOUND: "${text}"`, 'export', timestamp);
            this.logElementStructureSafe(item, timestamp);
          }
        }
      });
    } catch (error) {
      console.warn('Menu analysis error:', error.message);
    }
  }
  
  analyzeDialogContentSafe(dialogElement, timestamp) {
    try {
      const buttons = dialogElement.querySelectorAll('button, [role="button"], input[type="submit"]');
      this.log(`   🔘 Dialog contains ${Math.min(buttons.length, 10)} buttons`, 'detail', timestamp);
      
      // Limit to first 3 buttons to prevent lag
      const limitedButtons = Array.from(buttons).slice(0, 3);
      
      limitedButtons.forEach((button, index) => {
        const text = button.textContent?.trim();
        if (text && text.length < 50) { // Avoid very long text
          if (text.toLowerCase().includes('export')) {
            this.log(`     🎯 EXPORT BUTTON FOUND: "${text}"`, 'export', timestamp);
            this.logElementStructureSafe(button, timestamp);
          }
        }
      });
    } catch (error) {
      console.warn('Dialog analysis error:', error.message);
    }
  }
  
  logElementStructureSafe(element, timestamp) {
    try {
      this.log(`   📐 Element: ${element.tagName}`, 'detail', timestamp);
      this.log(`     Classes: ${element.className.substring(0, 50)}`, 'detail', timestamp);
      this.log(`     Text: "${element.textContent?.trim().substring(0, 30)}..."`, 'detail', timestamp);
    } catch (error) {
      console.warn('Element logging error:', error.message);
    }
  }
  
  setupEventListeners() {
    // Enhanced event monitoring with better detection
    console.log('🔍 Setting up enhanced event listeners...');
    
    // Monitor ALL click events (more comprehensive)
    document.addEventListener('click', (event) => {
      if (!this.isMonitoring) return;
      
      const timestamp = Date.now() - this.startTime;
      const element = event.target;
      const text = element.textContent?.trim();
      
      // Log ALL clicks during monitoring
      this.log(`🖱️ Click: "${text?.substring(0, 30) || '[no text]'}" (${element.tagName})`, 'click', timestamp);
      
      // Check for export-related clicks
      if (text && text.toLowerCase().includes('export')) {
        this.log(`🎯 EXPORT CLICK DETECTED!`, 'export', timestamp);
        this.logElementStructureSafe(element, timestamp);
      }
      
      // Check for any menu item clicks
      const role = element.getAttribute('role');
      if (role === 'menuitem' || element.closest('[role="menuitem"]')) {
        this.log(`📋 Menu item clicked: "${text?.substring(0, 30) || '[no text]'}"`, 'menu', timestamp);
      }
      
      // Check for button clicks
      if (element.tagName === 'BUTTON' || role === 'button') {
        this.log(`🔘 Button clicked: "${text?.substring(0, 30) || '[no text]'}"`, 'button', timestamp);
      }
    }, true);
    
    // Monitor context menu (right-click) - ALWAYS log
    document.addEventListener('contextmenu', (event) => {
      if (!this.isMonitoring) return;
      
      const timestamp = Date.now() - this.startTime;
      this.log(`🖱️ RIGHT-CLICK on: ${event.target.tagName}`, 'context', timestamp);
      this.log(`  Target classes: ${event.target.className}`, 'detail', timestamp);
      this.log(`  Target text: "${event.target.textContent?.trim().substring(0, 30) || '[no text]'}"`, 'detail', timestamp);
    }, true);
    
    // Monitor keyboard events
    document.addEventListener('keydown', (event) => {
      if (!this.isMonitoring) return;
      
      const timestamp = Date.now() - this.startTime;
      this.log(`⌨️ Key pressed: ${event.key}`, 'key', timestamp);
    }, true);
    
    // Monitor mouse events for comprehensive tracking
    document.addEventListener('mousedown', (event) => {
      if (!this.isMonitoring) return;
      
      if (event.button === 2) { // Right mouse button
        const timestamp = Date.now() - this.startTime;
        this.log(`🖱️ Mouse right-button down`, 'mouse', timestamp);
      }
    }, true);
  }
  
  attachGlobalListeners() {
    // Listen for messages from popup
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === 'startMonitoring') {
        this.startMonitoring();
        sendResponse({success: true});
      } else if (request.action === 'stopMonitoring') {
        this.stopMonitoring();
        sendResponse({success: true});
      } else if (request.action === 'getReport') {
        sendResponse({success: true, report: this.generateReport()});
      }
    });
  }
  
  log(message, type = 'info', timestamp = null) {
    const logEntry = {
      timestamp: timestamp || (Date.now() - this.startTime),
      type,
      message,
      time: new Date().toLocaleTimeString()
    };
    
    this.eventLogs.push(logEntry);
    
    // Limit log entries to prevent memory issues
    if (this.eventLogs.length > 200) {
      this.eventLogs = this.eventLogs.slice(-100);
    }
    
    // Update UI with throttling
    this.updateUILog(logEntry);
    
    // Console logging (less verbose)
    if (type === 'export' || type === 'menu' || type === 'dialog') {
      console.log(`[Monitor] ${message}`);
    }
  }
  
  updateUILog(logEntry) {
    const logDiv = document.getElementById('tv-monitor-log');
    if (!logDiv) return;
    
    try {
      const logElement = document.createElement('div');
      logElement.style.cssText = this.getLogStyle(logEntry.type);
      
      const timeStr = logEntry.timestamp ? `+${Math.round(logEntry.timestamp/1000)}s` : 'now';
      logElement.innerHTML = `<span style="color: #666;">[${timeStr}]</span> ${logEntry.message}`;
      
      logDiv.appendChild(logElement);
      logDiv.scrollTop = logDiv.scrollHeight;
      
      // Keep only last 50 log entries in UI to prevent DOM bloat
      while (logDiv.children.length > 50) {
        logDiv.removeChild(logDiv.firstChild);
      }
    } catch (error) {
      console.warn('UI log update error:', error.message);
    }
  }
  
  getLogStyle(type) {
    const styles = {
      info: 'color: #2196F3; margin: 2px 0;',
      export: 'color: #4CAF50; font-weight: bold; margin: 2px 0;',
      menu: 'color: #FF9800; margin: 2px 0;',
      dialog: 'color: #9C27B0; margin: 2px 0;',
      click: 'color: #F44336; margin: 2px 0;',
      context: 'color: #795548; margin: 2px 0;',
      key: 'color: #607D8B; margin: 2px 0;',
      attr: 'color: #CDDC39; margin: 2px 0;',
      detail: 'color: #999; margin: 1px 0; padding-left: 10px; font-size: 11px;'
    };
    return styles[type] || styles.info;
  }
  
  clearLog() {
    this.eventLogs = [];
    const logDiv = document.getElementById('tv-monitor-log');
    if (logDiv) {
      logDiv.innerHTML = '';
    }
    console.clear();
    this.log('🧹 Log cleared', 'info');
  }
  
  generateReport() {
    const report = {
      sessionId: this.sessionId,
      duration: this.startTime ? Date.now() - this.startTime : 0,
      totalEvents: this.eventLogs.length,
      exportEvents: this.eventLogs.filter(log => log.type === 'export'),
      menuEvents: this.eventLogs.filter(log => log.type === 'menu'),
      dialogEvents: this.eventLogs.filter(log => log.type === 'dialog'),
      clickEvents: this.eventLogs.filter(log => log.type === 'click'),
      contextEvents: this.eventLogs.filter(log => log.type === 'context'),
      allEvents: this.eventLogs,
      timestamp: new Date().toISOString()
    };
    
    console.log(`📊 Report generated: ${report.totalEvents} events, ${report.exportEvents.length} export-related`);
    
    // Force download report even if no events (for debugging)
    this.downloadReport(report);
    
    // Also log report to console for immediate viewing
    console.log('📋 FULL REPORT:', JSON.stringify(report, null, 2));
    
    return report;
  }
  
  downloadReport(report) {
    try {
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tradingview-monitor-${this.sessionId}.json`;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      this.log('💾 Report downloaded to Downloads folder', 'info');
      console.log('💾 Report download triggered successfully');
    } catch (error) {
      console.error('❌ Download failed:', error);
      this.log(`❌ Download failed: ${error.message}`, 'info');
      
      // Fallback: Copy to clipboard
      try {
        navigator.clipboard.writeText(JSON.stringify(report, null, 2));
        this.log('📋 Report copied to clipboard as fallback', 'info');
      } catch (clipError) {
        this.log('❌ Clipboard fallback also failed', 'info');
      }
    }
  }
}

// Initialize the monitor
console.log('🔍 TradingView Monitor: Starting initialization...');
const tradingViewMonitor = new TradingViewMonitor();

// Global access for debugging
window.tvMonitor = tradingViewMonitor;

console.log('✅ TradingView Monitor: Loaded and ready!');
console.log('💡 Use window.tvMonitor to access the monitor programmatically');