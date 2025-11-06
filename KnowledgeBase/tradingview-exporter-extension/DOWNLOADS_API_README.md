# 🚀 TradingView Exporter - Enhanced Downloads API Integration

## Overview

This Chrome extension has been significantly enhanced with **Chrome Downloads API** integration, inspired by the [Chrome DevTools Autosave](https://github.com/NV/chrome-devtools-autosave) project architecture. The new system provides automated download management, smart file naming, and comprehensive monitoring.

## ✨ New Features Powered by Downloads API

### 🎯 Automatic Download Detection

- **Real-time monitoring** of TradingView CSV exports
- **Smart identification** of export downloads vs regular downloads
- **Queue management** for multiple simultaneous exports

### 📁 Smart File Management

- **Intelligent filenames**: `chart_export_BTCUSD_2025-11-03_143025.csv`
- **Automatic folder organization**: Downloads/TradingView_Data/
- **Conflict resolution**: uniquify, overwrite, or prompt options
- **Symbol extraction** from page context and download metadata

### 🔔 Enhanced Notifications

- **Download progress** notifications
- **Completion confirmations** with file locations
- **Error handling** with detailed failure reasons
- **Visual indicators** on the TradingView page

### ⚙️ Configurable Settings

- **Custom download paths** and file prefixes
- **Enable/disable auto-save** functionality
- **Notification preferences**
- **Conflict handling strategies**

## 🔧 Technical Implementation

### Architecture Inspired by Chrome DevTools Autosave

The implementation follows the **server-client** pattern from Chrome DevTools Autosave:

```javascript
// Background Script (Server-like)
chrome.downloads.onCreated.addListener((downloadItem) => {
  // Similar to DevTools Autosave's onResourceContentCommitted
  if (isTradingViewExport(downloadItem)) {
    handleTradingViewDownload(downloadItem);
  }
});

// Content Script (Client-like)
chrome.runtime.sendMessage({
  action: "exportWithDownloadsAPI",
  settings: exportSettings,
});
```

### Key Components

1. **Background Script Enhancement** (`background.js`)

   - Downloads API event monitoring
   - Smart filename generation
   - Notification management
   - Download queue tracking

2. **Content Script Integration** (`content.js`)

   - Symbol extraction from TradingView page
   - Export workflow automation
   - Background script communication

3. **Popup UI Extensions** (`popup.html/js`)

   - Downloads API settings configuration
   - Real-time status updates
   - Download preferences management

4. **Download Helper Utility** (`download-helper.js`)
   - Reusable download management class
   - Programmatic download initiation
   - Advanced search and filtering

## 🚀 Usage Guide

### Basic Auto-Export

1. **Open** the extension popup on a TradingView chart
2. **Configure** symbol and exchange (or use quick-select buttons)
3. **Enable** "Auto-save with smart filenames"
4. **Click** "Export Visible Data"
5. **Watch** as the file automatically saves with intelligent naming!

### Advanced Configuration

#### Smart Download Settings

```javascript
// Customize in popup or programmatically
const settings = {
  autoSave: true,
  downloadPath: "TradingView_Analysis",
  filePrefix: "market_data_",
  enableNotifications: true,
  conflictAction: "uniquify",
};
```

#### Programmatic Usage

```javascript
// Use the download helper class
const manager = new TradingViewDownloadManager();

// Initiate custom download
await manager.initiateDownload("blob:...", "custom_export.csv", {
  saveAs: false,
});

// Search existing downloads
const recentExports = await manager.searchDownloads({
  query: ["tradingview"],
  limit: 10,
});
```

## 🆕 What's Different from Standard Approach

### Before (Manual Save Dialog)

1. User clicks export
2. Browser shows save dialog
3. User manually selects location and filename
4. User clicks Save button
5. File saved with generic name

### After (Downloads API Integration)

1. User clicks export
2. **Extension detects download automatically**
3. **Smart filename generated** (symbol + timestamp)
4. **File saved to organized folder structure**
5. **Notification confirms success** with file location

## 🔍 Comparison with Chrome DevTools Autosave

| Feature             | DevTools Autosave          | Our TradingView Extension |
| ------------------- | -------------------------- | ------------------------- |
| **Trigger**         | CSS/JS edit in DevTools    | TradingView export action |
| **Content**         | Modified source code       | Chart data CSV            |
| **Architecture**    | Extension + Node.js server | Extension + Downloads API |
| **File Resolution** | URL → file path mapping    | Symbol + timestamp naming |
| **Auto-save**       | ✅ Real-time               | ✅ On export              |
| **Notifications**   | ❌ None                    | ✅ Rich notifications     |

## 🛠️ Installation & Setup

### Required Permissions

```json
{
  "permissions": [
    "storage",
    "downloads", // ← New: For Downloads API
    "notifications" // ← New: For status notifications
  ]
}
```

### Development Setup

1. **Clone** this repository
2. **Load** extension in Chrome Developer Mode
3. **Grant** Downloads and Notifications permissions
4. **Open** TradingView chart
5. **Test** export functionality

### Browser Compatibility

- ✅ **Chrome 88+** (Downloads API stable)
- ✅ **Edge 88+** (Chromium-based)
- ❌ **Firefox** (Different WebExtensions API)

## 📊 Monitoring & Debugging

### Console Output

The extension provides detailed logging:

```
🎯 TradingView CSV export detected
🧠 Generating smart filename for TradingView export...
📁 Smart filename: TradingView_Data/chart_export_BTCUSD_2025-11-03_143025.csv
✅ Export completed: chart_export_BTCUSD_2025-11-03_143025.csv
```

### Download Queue Inspection

```javascript
// In background script console
console.log("Active downloads:", downloadQueue);

// In popup console
chrome.runtime.sendMessage({ action: "getDownloadStatus" });
```

## 🔒 Security & Privacy

### Downloads API Security Model

- **Same-origin enforcement**: Only TradingView downloads processed
- **User permission required**: Downloads API needs explicit user consent
- **Sandboxed execution**: Extension runs in isolated context
- **No server dependency**: All processing happens locally

### Data Handling

- **No cloud uploads**: All data stays on user's machine
- **Local file management**: Downloads API respects user's download settings
- **Minimal data collection**: Only download metadata for smart naming

## 🐛 Troubleshooting

### Downloads API Not Working

```javascript
// Check API availability
if (!chrome.downloads) {
  console.error("Downloads API not available");
}

// Check permissions
chrome.permissions.contains({ permissions: ["downloads"] }, (result) => {
  console.log("Downloads permission:", result);
});
```

### Common Issues

1. **Extension not detecting exports**: Check TradingView page URL patterns
2. **Smart filenames not working**: Verify symbol extraction in console
3. **Notifications not showing**: Check notification permissions in Chrome settings
4. **Files not auto-saving**: Ensure "Auto-save with smart filenames" is enabled

## 🚗 Roadmap

### Planned Enhancements

- [ ] **Bulk export management** for multiple timeframes
- [ ] **Custom filename templates** with variables
- [ ] **Export scheduling** with Downloads API
- [ ] **Cloud storage integration** (Google Drive, OneDrive)
- [ ] **Download analytics** and usage statistics

### Advanced Features

- [ ] **Server-side component** (like DevTools Autosave server)
- [ ] **Real-time sync** across multiple browser instances
- [ ] **Advanced conflict resolution** with diff comparison
- [ ] **Export templates** for different analysis workflows

## 📚 References

- [Chrome Downloads API Documentation](https://developer.chrome.com/docs/extensions/reference/api/downloads)
- [Chrome DevTools Autosave Project](https://github.com/NV/chrome-devtools-autosave)
- [WebExtensions API Guide](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions)
- [TradingView API Documentation](https://www.tradingview.com/charting-library-docs/)

## 🤝 Contributing

Contributions welcome! Areas of focus:

- Download workflow optimization
- Smart naming algorithm improvements
- Additional export format support
- Cross-browser compatibility

---

_This enhanced version transforms the extension from a simple automation tool into a comprehensive download management system, providing the same level of sophistication as professional development tools like Chrome DevTools Autosave._
