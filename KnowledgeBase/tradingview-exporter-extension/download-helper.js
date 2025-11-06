// download-helper.js - Enhanced Downloads API Helper Functions
// Demonstrates advanced download management inspired by Chrome DevTools Autosave

console.log('📥 Downloads API Helper Loaded');

/**
 * Download Manager - Inspired by Chrome DevTools Autosave approach
 * Provides programmatic download management for TradingView exports
 */
class TradingViewDownloadManager {
  constructor() {
    this.downloadQueue = new Map();
    this.settings = {
      autoSave: true,
      smartFilenames: true,
      downloadPath: 'TradingView_Data',
      filePrefix: 'tradingview_',
      notifications: true,
      conflictAction: 'uniquify' // 'uniquify', 'overwrite', 'prompt'
    };
    
    this.initializeDownloadMonitoring();
  }
  
  /**
   * Initialize download monitoring (similar to DevTools Autosave server approach)
   */
  initializeDownloadMonitoring() {
    if (!chrome.downloads) {
      console.warn('⚠️ Downloads API not available');
      return;
    }
    
    console.log('🔄 Initializing Downloads API monitoring...');
    
    // Monitor download creation
    chrome.downloads.onCreated.addListener((downloadItem) => {
      this.handleDownloadCreated(downloadItem);
    });
    
    // Monitor download changes
    chrome.downloads.onChanged.addListener((downloadDelta) => {
      this.handleDownloadChanged(downloadDelta);
    });
    
    // Monitor download completion
    chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
      this.handleFilenameGeneration(downloadItem, suggest);
    });
    
    console.log('✅ Downloads API monitoring active');
  }
  
  /**
   * Handle new download creation (like DevTools Autosave onResourceContentCommitted)
   */
  handleDownloadCreated(downloadItem) {
    console.log('📥 Download created:', downloadItem);
    
    // Check if this is a TradingView export
    if (this.isTradingViewExport(downloadItem)) {
      console.log('🎯 TradingView export detected');
      
      this.downloadQueue.set(downloadItem.id, {
        item: downloadItem,
        timestamp: Date.now(),
        type: 'tradingview_csv',
        processed: false
      });
      
      if (this.settings.notifications) {
        this.showNotification('📥 TradingView Export Detected', 
                            `Processing: ${downloadItem.filename}`);
      }
    }
  }
  
  /**
   * Handle download state changes
   */
  handleDownloadChanged(downloadDelta) {
    if (!this.downloadQueue.has(downloadDelta.id)) return;
    
    const download = this.downloadQueue.get(downloadDelta.id);
    
    if (downloadDelta.state) {
      switch (downloadDelta.state.current) {
        case 'complete':
          this.handleDownloadComplete(download, downloadDelta);
          break;
        case 'interrupted':
          this.handleDownloadFailed(download, downloadDelta);
          break;
      }
    }
  }
  
  /**
   * Generate smart filenames (inspired by DevTools Autosave path resolution)
   */
  handleFilenameGeneration(downloadItem, suggest) {
    if (!this.isTradingViewExport(downloadItem)) {
      suggest(); // Use default filename
      return true;
    }
    
    if (!this.settings.smartFilenames) {
      suggest(); // Use default filename
      return true;
    }
    
    console.log('🧠 Generating smart filename for TradingView export...');
    
    // Extract symbol from various sources
    const symbol = this.extractSymbol(downloadItem);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
    const time = new Date().toTimeString().split(' ')[0].replace(/:/g, '');
    
    // Generate smart filename
    const smartFilename = `${this.settings.filePrefix}${symbol}_${timestamp}_${time}.csv`;
    const downloadPath = `${this.settings.downloadPath}/${smartFilename}`;
    
    console.log(`📁 Smart filename: ${downloadPath}`);
    
    suggest({
      filename: downloadPath,
      conflictAction: this.settings.conflictAction
    });
    
    return true;
  }
  
  /**
   * Check if download is a TradingView export
   */
  isTradingViewExport(downloadItem) {
    // Check URL patterns
    if (downloadItem.url && downloadItem.url.includes('blob:')) {
      // Check filename patterns
      if (downloadItem.filename && 
          downloadItem.filename.toLowerCase().includes('.csv')) {
        return true;
      }
    }
    
    // Check referrer
    if (downloadItem.referrer && 
        downloadItem.referrer.includes('tradingview.com')) {
      return true;
    }
    
    return false;
  }
  
  /**
   * Extract symbol from download context
   */
  extractSymbol(downloadItem) {
    // Try to extract from filename
    if (downloadItem.filename) {
      const filenameMatch = downloadItem.filename.match(/([A-Z0-9]+)[_\-\.]/);
      if (filenameMatch) {
        return filenameMatch[1];
      }
    }
    
    // Try to extract from referrer URL
    if (downloadItem.referrer) {
      const urlMatch = downloadItem.referrer.match(/symbol=([^&]+)/);
      if (urlMatch) {
        return decodeURIComponent(urlMatch[1]).replace(/[^A-Z0-9]/g, '_');
      }
    }
    
    return 'UNKNOWN';
  }
  
  /**
   * Handle successful download completion
   */
  handleDownloadComplete(download, downloadDelta) {
    console.log('✅ TradingView export completed:', download.item.filename);
    
    if (this.settings.notifications) {
      this.showNotification('✅ Export Complete', 
                          `Saved: ${download.item.filename}`);
    }
    
    // Clean up after delay
    setTimeout(() => {
      this.downloadQueue.delete(download.item.id);
    }, 5000);
  }
  
  /**
   * Handle failed downloads
   */
  handleDownloadFailed(download, downloadDelta) {
    console.error('❌ TradingView export failed:', downloadDelta.error);
    
    if (this.settings.notifications) {
      this.showNotification('❌ Export Failed', 
                          `Error: ${downloadDelta.error?.current || 'Unknown error'}`);
    }
  }
  
  /**
   * Show notification
   */
  showNotification(title, message) {
    if (!chrome.notifications) return;
    
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: title,
      message: message
    });
  }
  
  /**
   * Programmatically initiate download (like DevTools Autosave server)
   */
  async initiateDownload(url, filename, options = {}) {
    if (!chrome.downloads) {
      throw new Error('Downloads API not available');
    }
    
    const downloadOptions = {
      url: url,
      filename: filename || undefined,
      saveAs: options.saveAs || false,
      conflictAction: options.conflictAction || this.settings.conflictAction,
      ...options
    };
    
    console.log('🚀 Initiating programmatic download:', downloadOptions);
    
    try {
      const downloadId = await chrome.downloads.download(downloadOptions);
      console.log('✅ Download initiated with ID:', downloadId);
      return downloadId;
    } catch (error) {
      console.error('❌ Download initiation failed:', error);
      throw error;
    }
  }
  
  /**
   * Search and manage existing downloads
   */
  async searchDownloads(query = {}) {
    if (!chrome.downloads) return [];
    
    try {
      const downloads = await chrome.downloads.search(query);
      console.log(`📋 Found ${downloads.length} downloads`);
      return downloads;
    } catch (error) {
      console.error('❌ Download search failed:', error);
      return [];
    }
  }
  
  /**
   * Update settings
   */
  updateSettings(newSettings) {
    this.settings = { ...this.settings, ...newSettings };
    console.log('⚙️ Download manager settings updated:', this.settings);
  }
}

// Initialize global download manager
if (typeof window !== 'undefined') {
  window.TradingViewDownloadManager = TradingViewDownloadManager;
  console.log('✅ TradingView Download Manager available globally');
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TradingViewDownloadManager;
}