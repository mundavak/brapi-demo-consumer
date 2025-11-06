// stealth.js - Advanced Anti-Detection
// Injected into page context to hide automation traces

(function() {
  'use strict';
  
  // 1. Override webdriver detection
  Object.defineProperty(navigator, 'webdriver', {
    get: () => false,
    configurable: true
  });
  
  // 2. Hide chrome extension APIs
  if (window.chrome && window.chrome.runtime) {
    delete window.chrome.runtime;
    delete window.chrome.extension;
  }
  
  // 3. Spoof plugin detection
  Object.defineProperty(navigator, 'plugins', {
    get: () => {
      return {
        length: 3,
        0: { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
        1: { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
        2: { name: 'Native Client', filename: 'internal-nacl-plugin' }
      };
    },
    configurable: true
  });
  
  // 4. Override permission queries
  if (navigator.permissions && navigator.permissions.query) {
    const originalQuery = navigator.permissions.query;
    navigator.permissions.query = function(parameters) {
      if (parameters.name === 'notifications') {
        return Promise.resolve({ state: 'granted' });
      }
      return originalQuery.apply(this, arguments);
    };
  }
  
  // 5. Hide automation timing patterns
  const originalSetTimeout = window.setTimeout;
  const originalSetInterval = window.setInterval;
  
  window.setTimeout = function(callback, delay, ...args) {
    // Add slight random variation to timeouts
    const randomDelay = delay + (Math.random() - 0.5) * Math.min(delay * 0.1, 10);
    return originalSetTimeout.call(this, callback, randomDelay, ...args);
  };
  
  window.setInterval = function(callback, delay, ...args) {
    // Add slight random variation to intervals
    const randomDelay = delay + (Math.random() - 0.5) * Math.min(delay * 0.05, 5);
    return originalSetInterval.call(this, callback, randomDelay, ...args);
  };
  
  // 6. Spoof language and timezone consistency
  Object.defineProperty(navigator, 'language', {
    get: () => 'en-US',
    configurable: true
  });
  
  Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
    configurable: true
  });
  
  // 7. Hide extension content script traces
  const scripts = document.querySelectorAll('script[src*="extension"]');
  scripts.forEach(script => script.remove());
  
  // 8. Override Date to avoid timezone detection
  const originalDate = Date;
  const timezoneOffset = -300; // EST timezone
  
  Date.prototype.getTimezoneOffset = function() {
    return timezoneOffset;
  };
  
  // 9. Spoof screen properties
  Object.defineProperty(screen, 'colorDepth', {
    get: () => 24,
    configurable: true
  });
  
  Object.defineProperty(screen, 'pixelDepth', {
    get: () => 24,
    configurable: true
  });
  
  // 10. Hide mouse automation patterns
  const originalAddEventListener = Element.prototype.addEventListener;
  Element.prototype.addEventListener = function(type, listener, options) {
    if (type === 'mousemove' || type === 'mousedown' || type === 'mouseup') {
      // Wrap mouse event listeners to add natural variations
      const wrappedListener = function(event) {
        // Add slight random delays to mouse events
        setTimeout(() => listener.call(this, event), Math.random() * 2);
      };
      return originalAddEventListener.call(this, type, wrappedListener, options);
    }
    return originalAddEventListener.call(this, type, listener, options);
  };
  
  // 11. Hide extension detection via error stack traces
  const originalError = Error;
  Error = function(...args) {
    const error = new originalError(...args);
    if (error.stack) {
      error.stack = error.stack.replace(/chrome-extension:\/\/[a-z]+/g, 'https://www.tradingview.com');
    }
    return error;
  };
  Error.prototype = originalError.prototype;
  
  console.log('🥷 Stealth mode activated - Human simulation enabled');
})();