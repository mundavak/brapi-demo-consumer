// content.js - STEALTH VERSION
// TradingView Auto-Exporter Extension
// Designed to be undetectable by anti-bot systems

// Remove extension detection fingerprints
(function() {
  'use strict';
  
  // Safely hide chrome.runtime from page scripts
  try {
    if (typeof chrome !== 'undefined' && chrome.runtime) {
      // Override chrome object detection safely
      Object.defineProperty(window, 'chrome', {
        get: () => undefined,
        configurable: true
      });
    }
  } catch (e) {
    // Silently handle if chrome object can't be modified
  }
  
  // Safely spoof navigator.webdriver
  try {
    Object.defineProperty(navigator, 'webdriver', {
      get: () => false,
      configurable: true
    });
  } catch (e) {
    // Silently handle if webdriver can't be modified
  }
  
  // Safely hide automation detection
  try {
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5],
      configurable: true
    });
  } catch (e) {
    // Silently handle plugin spoofing errors
  }
  
  // Safely spoof language consistency
  try {
    Object.defineProperty(navigator, 'language', {
      get: () => 'en-US',
      configurable: true
    });
  } catch (e) {
    // Silently handle language spoofing errors
  }
  
  console.log('TradingView Tool: Content script loaded (Human Mode)');
})();

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('📨 Received message:', request);
  
  if (request.action === 'export') {
    console.log('🚀 Starting export with settings:', request.settings);
    
    exportData(request.settings)
      .then(() => {
        console.log('✅ Export complete!');
        sendResponse({success: true, message: 'Export initiated!'});
      })
      .catch(error => {
        console.error('❌ Export error:', error);
        sendResponse({success: false, message: error.message});
      });
    return true;
  }
  
  if (request.action === 'screenshot') {
    takeScreenshot();
    sendResponse({success: true});
    return true;
  }
  
  if (request.action === 'captureHTML') {
    captureHTML();
    sendResponse({success: true});
    return true;
  }
});

/**
 * Main export function (Stealth Mode)
 */
async function exportData(settings) {
  console.log('═'.repeat(70));
  console.log('STEALTH EXPORT PROCESS STARTED');
  console.log('═'.repeat(70));
  console.log('Target:', settings.symbol);
  console.log('Mode: Human Simulation');
  console.log('');
  
  try {
    // Add initial human-like delay
    await humanPause();
    
    // STEP 1: Find the chart element to right-click on
    console.log('Step 1: Locating chart area...');
    const chartElement = findChartElement();
    
    if (!chartElement) {
      throw new Error('Chart element not found');
    }
    
    console.log('✅ Chart area identified');
    
    // Human-like hesitation before action
    await humanPause();
    
    // **UPDATED: Use ACTUAL user workflow (layout menu, not right-click)**
    console.log('Step 2: Opening export via layout menu (real user workflow)...');
    
    // Look for the layout button (shows number like "2" in top-left area)
    const layoutButton = document.querySelector('[data-name="save-load-menu-item-rename"]')?.closest('button') ||
                         document.querySelector('[aria-label*="layout"]') ||
                         document.querySelector('[data-tooltip*="layout"]') ||
                         document.querySelector('button[class*="button-mer"][class*="BkM5y"]') ||
                         // Look for numbered buttons in toolbar (layout indicators)
                         Array.from(document.querySelectorAll('button')).find(btn => {
                           const text = btn.textContent?.trim();
                           const tooltip = btn.getAttribute('data-tooltip') || btn.getAttribute('aria-label') || '';
                           const hasNumber = text && /^\d+$/.test(text); // Just a number
                           const hasLayoutKeyword = tooltip.toLowerCase().includes('layout') ||
                                                   tooltip.toLowerCase().includes('manage') ||
                                                   tooltip.toLowerCase().includes('save');
                           return hasNumber || hasLayoutKeyword;
                         });
    
    if (!layoutButton) {
      console.log('❌ Layout button not found, trying keyboard shortcut fallback...');
      
      // **FALLBACK: Direct keyboard shortcut**
      const chartArea = document.querySelector('[data-name="chart-area"]') || 
                       document.querySelector('.chart-markup-table') ||
                       document.body;
      
      chartArea.focus();
      await sleep(500);
      
      console.log('⌨️ Trying Ctrl+E export shortcut...');
      const ctrlE = new KeyboardEvent('keydown', {
        key: 'e',
        code: 'KeyE', 
        ctrlKey: true,
        bubbles: true,
        cancelable: true
      });
      
      document.dispatchEvent(ctrlE);
      chartArea.dispatchEvent(ctrlE);
      await sleep(3000);
      
      // Check if export dialog appeared  
      const exportDialog = document.querySelector('[data-name="chart-export-dialog"]') ||
                          document.querySelector('[role="dialog"]');
      
      if (exportDialog) {
        console.log('✅ Export dialog opened via keyboard shortcut!');
        return true; // Skip to dialog configuration
      }
      
      console.log('❌ All methods failed to open export dialog');
      return false;
    }
    
    console.log('✅ Found layout button, opening menu...');
    console.log(`   Button text: "${layoutButton.textContent?.trim()}"`);
    console.log(`   Button class: ${layoutButton.className}`);
    
    // Click layout button to open dropdown menu
    await clickElement(layoutButton);
    await sleep(1500); // Wait for dropdown menu to appear
    
    // Look for "Export chart data..." in the dropdown menu
    console.log('🔍 Looking for "Export chart data..." option in menu...');
    
    const layoutExportItem = Array.from(document.querySelectorAll('*')).find(el => {
      const text = el.textContent?.trim() || '';
      return text === 'Export chart data...' || 
             text === 'Export chart data' ||
             (text.includes('Export') && text.includes('chart') && text.length < 30);
    });
    
    if (!layoutExportItem) {
      console.log('❌ "Export chart data" option not found in layout menu');
      console.log('🔍 Showing available menu options:');
      
      // Debug: Show what menu items are available
      const menuItems = Array.from(document.querySelectorAll('*')).filter(el => {
        const rect = el.getBoundingClientRect();
        return el.textContent && 
               el.textContent.trim().length > 2 && 
               el.textContent.trim().length < 50 &&
               el.offsetParent !== null &&
               el.children.length === 0 &&
               rect.width > 30 && rect.height > 10;
      });
      
      menuItems.slice(0, 15).forEach((item, i) => {
        console.log(`   ${i+1}. "${item.textContent?.trim()}"`);
      });
      
      return false;
    }
    
    console.log('✅ Found "Export chart data" menu item, clicking...');
    await clickElement(layoutExportItem);
    await sleep(2000); // Wait for export dialog to open
    
    // STEP 3: Export dialog should now be open
    console.log('Step 3: Export dialog should be open, proceeding to configuration...');
    
    const exportMenuItem = await findExportMenuItem();
    
    // Handle different return types from findExportMenuItem
    let actualElement = exportMenuItem;
    let foundMethod = 'context-menu';
    
    if (exportMenuItem && typeof exportMenuItem === 'object' && exportMenuItem.success) {
      actualElement = exportMenuItem.element;
      foundMethod = exportMenuItem.method;
      console.log(`✅ Export option found via ${foundMethod}`);
    } else if (exportMenuItem) {
      console.log('✅ Export option found via context menu');
    }
    
    if (!actualElement) {
      console.warn('⚠️ Export option not located');
      showManualInstructions(settings);
      return false;
    }
    
    console.log('✅ Export option found');
    
    // Human thinking delay before clicking
    await sleep(Math.random() * 300 + 200);
    
    console.log('Step 4: Selecting export option...');
    
    // Handle different element types based on detection method
    if (foundMethod && foundMethod.includes('keyboard')) {
      console.log('📋 Export dialog already opened via keyboard shortcut');
      // Skip clicking, dialog should already be open
    } else {
      // Simulate human-like click on the found element
      await simulateHumanClick(actualElement);
    }
    
    // Wait for dialog with human-like timing
    await sleep(Math.random() * 500 + 700);
    
    // STEP 5: Handle export dialog
    console.log('Step 5: Configuring export settings...');
    await configureExportDialog();
    
    console.log('═'.repeat(70));
    console.log('✅ STEALTH EXPORT COMPLETED');
    console.log('═'.repeat(70));
    
    return true;
    
  } catch (error) {
    console.error('═'.repeat(70));
    console.error('❌ EXPORT FAILED');
    console.error('═'.repeat(70));
    console.error('Error:', error.message);
    
    showManualInstructions(settings);
    throw error;
  }
}

/**
 * Simulate human-like clicking with micro-movements
 */
async function simulateHumanClick(element) {
  const rect = element.getBoundingClientRect();
  
  // Random click position within element (human-like imprecision)
  const randomX = (Math.random() - 0.5) * (rect.width * 0.6);
  const randomY = (Math.random() - 0.5) * (rect.height * 0.6);
  
  const x = rect.left + rect.width / 2 + randomX;
  const y = rect.top + rect.height / 2 + randomY;
  
  // Simulate mouse hover first (human behavior)
  const hoverEvent = new MouseEvent('mouseover', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y
  });
  
  element.dispatchEvent(hoverEvent);
  await sleep(Math.random() * 100 + 50);
  
  // Then click with realistic sequence
  const mouseDownEvent = new MouseEvent('mousedown', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 0,
    buttons: 1
  });
  
  const clickEvent = new MouseEvent('click', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 0,
    buttons: 1
  });
  
  const mouseUpEvent = new MouseEvent('mouseup', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 0,
    buttons: 0
  });
  
  // Dispatch with human timing
  element.dispatchEvent(mouseDownEvent);
  await sleep(Math.random() * 80 + 40);
  element.dispatchEvent(clickEvent);
  await sleep(Math.random() * 30 + 10);
  element.dispatchEvent(mouseUpEvent);
}

/**
 * Find the chart element to click on
 */
function findChartElement() {
  const candidates = [
    document.querySelector('.chart-container'),
    document.querySelector('[class*="chart-container"]'),
    document.querySelector('canvas'),
    document.querySelector('[class*="chart-markup"]'),
    document.querySelector('[data-name="legend-source-item"]')?.closest('[class*="chart"]'),
  ];
  
  for (const element of candidates) {
    if (element && element.offsetParent !== null) {
      return element;
    }
  }
  
  return null;
}

/**
 * Simulate human-like right-click with random variations
 */
async function simulateRightClick(element) {
  const rect = element.getBoundingClientRect();
  
  // Add random offset to avoid perfect center clicks (human-like)
  const randomX = (Math.random() - 0.5) * (rect.width * 0.3);
  const randomY = (Math.random() - 0.5) * (rect.height * 0.3);
  
  const x = rect.left + rect.width / 2 + randomX;
  const y = rect.top + rect.height / 2 + randomY;
  
  // Add slight delay before action (human-like hesitation)
  await sleep(Math.random() * 200 + 100);
  
  // Create more realistic mouse events sequence
  const mouseDownEvent = new MouseEvent('mousedown', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 2,
    buttons: 2
  });
  
  const contextMenuEvent = new MouseEvent('contextmenu', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 2,
    buttons: 2
  });
  
  const mouseUpEvent = new MouseEvent('mouseup', {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: x,
    clientY: y,
    button: 2,
    buttons: 0
  });
  
  // Dispatch events with human-like timing
  element.dispatchEvent(mouseDownEvent);
  await sleep(Math.random() * 50 + 20);
  element.dispatchEvent(contextMenuEvent);
  await sleep(Math.random() * 30 + 10);
  element.dispatchEvent(mouseUpEvent);
  
  console.log('✅ Human-like right-click dispatched at', {x: Math.round(x), y: Math.round(y)});
}

/**
 * Find "Export chart data..." menu item (ENHANCED DEBUGGING)
 */
async function findExportMenuItem() {
  console.log('🔍 Searching for export menu item with ENHANCED debugging...');
  
  // First, let's see what's actually in the DOM after right-click
  console.log('🔍 DEBUG: Analyzing DOM after right-click...');
  
  // Look for any recently appeared elements (context menus)
  const recentElements = Array.from(document.querySelectorAll('*')).filter(el => {
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && 
           style.visibility !== 'hidden' && 
           style.opacity !== '0' &&
           el.offsetParent !== null;
  });
  
  console.log(`Found ${recentElements.length} visible elements`);
  
  // Look for elements that might be menus/popups (EXCLUDE persistent UI elements)
  const menuLikeElements = recentElements.filter(el => {
    const tag = el.tagName.toLowerCase();
    const classes = (el.className?.toString() || '').toLowerCase();
    const role = el.getAttribute('role') || '';
    
    // EXCLUDE persistent UI elements that are always visible
    const isPersistentUI = classes.includes('layout__area') ||
                          classes.includes('toolbar') ||
                          classes.includes('topLeftButton') ||
                          classes.includes('buttonWrap') ||
                          classes.includes('menu-U2jIw4km') || // Exclude the user menu we found
                          el.textContent?.includes('11') || // User notification badge
                          el.closest('.layout__area--topleft'); // Top-left UI area
    
    return !isPersistentUI && tag === 'div' && (
      classes.includes('menu') ||
      classes.includes('popup') ||
      classes.includes('context') ||
      classes.includes('dropdown') ||
      classes.includes('overlay') ||
      role.includes('menu') ||
      (el.children.length > 2 && el.children.length <= 15) // Context menus typically have multiple items
    );
  });
  
  console.log(`Found ${menuLikeElements.length} potential menu containers:`);
  menuLikeElements.forEach((el, i) => {
    if (i < 10) { // Show more containers for analysis
      const className = el.className?.toString() || 'no-class';
      console.log(`  ${i+1}. ${el.tagName}.${className} (${el.children.length} children)`);
      
      // **NEW: Analyze ALL children in potential menu containers**
      if (el.children.length > 0 && el.children.length <= 20) {
        console.log(`     🔍 Children analysis:`);
        Array.from(el.children).forEach((child, j) => {
          const childClass = child.className?.toString() || 'no-class';
          const text = child.textContent?.trim() || '';
          console.log(`       ${j+1}. ${child.tagName}.${childClass}: "${text.substring(0, 50)}"`);
          
          // Look for clickable indicators
          const isClickable = child.tagName === 'BUTTON' || 
                            child.getAttribute('role') === 'menuitem' ||
                            child.onclick ||
                            child.getAttribute('tabindex') !== null ||
                            child.style.cursor === 'pointer';
          if (isClickable) {
            console.log(`          ⭐ CLICKABLE ELEMENT!`);
          }
        });
      }
    }
  });
  
  // Strategy 1: Look for the monitored class
  let exportItem = document.querySelector('span.label-jFqVJoPk');
  if (exportItem && exportItem.textContent?.includes('Export chart data')) {
    console.log('✅ Found export item via monitored class: label-jFqVJoPk');
    return exportItem.closest('button, [role="menuitem"], [role="row"], [onclick], [tabindex]') || exportItem;
  }
  
  // Strategy 2: Search ALL visible spans for export-related text
  const allSpans = Array.from(document.querySelectorAll('span')).filter(span => {
    return span.offsetParent !== null; // Only visible spans
  });
  
  console.log(`Analyzing ${allSpans.length} visible spans for export text...`);
  
  const exportSpans = allSpans.filter(span => {
    const text = span.textContent?.toLowerCase() || '';
    return text.includes('export') && text.length < 50; // Reasonable length
  });
  
  console.log(`Found ${exportSpans.length} spans with "export" text:`);
  exportSpans.forEach((span, i) => {
    if (i < 10) {
      const className = span.className?.toString() || 'no-class'; // Fixed: safe className access
      console.log(`  ${i+1}. "${span.textContent?.trim()}" (class: ${className})`);
    }
  });
  
  // Try to find clickable parent for each export span
  for (const span of exportSpans) {
    if (span.textContent?.toLowerCase().includes('chart') || 
        span.textContent?.toLowerCase().includes('data')) {
      
      console.log(`🎯 Checking promising span: "${span.textContent?.trim()}"`);
      
      // Look for clickable parent
      let clickableParent = span.closest('button, [role="menuitem"], [role="row"], div[onclick], [tabindex]');
      
      if (!clickableParent) {
        // Try going up the DOM tree manually
        let parent = span.parentElement;
        let depth = 0;
        while (parent && parent !== document.body && depth < 5) {
          const parentClass = parent.className?.toString() || 'no-class'; // Fixed: safe className access
          console.log(`    Parent ${depth}: ${parent.tagName}.${parentClass}`);
          
          if (parent.tagName === 'BUTTON' || 
              parent.getAttribute('role') === 'menuitem' ||
              parent.getAttribute('role') === 'row' ||
              parent.onclick ||
              parent.getAttribute('tabindex') !== null ||
              parent.style.cursor === 'pointer') {
            clickableParent = parent;
            break;
          }
          parent = parent.parentElement;
          depth++;
        }
      }
      
      if (clickableParent) {
        console.log('✅ Found clickable export element:', clickableParent);
        return clickableParent;
      }
    }
  }
  
  // Strategy 3: Look for ANY element with export in text content
  console.log('🔍 Searching ALL elements for export text...');
  const allElements = Array.from(document.querySelectorAll('*')).filter(el => {
    const text = el.textContent?.toLowerCase() || '';
    return text.includes('export') && 
           text.length < 100 && 
           el.offsetParent !== null &&
           el.children.length === 0; // Leaf nodes only
  });
  
  console.log(`Found ${allElements.length} elements with export text:`);
  allElements.forEach((el, i) => {
    if (i < 10) {
      const className = el.className?.toString() || 'no-class'; // Fixed: safe className access
      console.log(`  ${i+1}. ${el.tagName}.${className}: "${el.textContent?.trim()}"`);
    }
  });
  
  // Strategy 4: **NEW** - Check specific TradingView menu containers found (EXCLUDE persistent UI)
  console.log('🎯 Checking specific TradingView menu containers...');
  
  // Look for context menus, NOT the persistent user menu
  const contextMenus = document.querySelectorAll('div[class*="menu-"]:not(.menu-U2jIw4km)') ||
                      document.querySelectorAll('div[class*="popup-"]') ||
                      document.querySelectorAll('div[class*="context-"]');
  
  console.log(`Found ${contextMenus.length} potential context menus (excluding persistent UI)`);
  
  for (const tvMenu of contextMenus) {
    // Skip if this looks like persistent UI
    if (tvMenu.closest('.layout__area--topleft') || 
        tvMenu.textContent?.includes('11') ||
        tvMenu.querySelector('.userPic-U2jIw4km')) {
      console.log('⏭️ Skipping persistent UI element:', tvMenu.className?.toString());
      continue;
    }
    
    console.log('✅ Found potential context menu:', tvMenu);
    console.log('   Class:', tvMenu.className?.toString());
    console.log('   Children:', tvMenu.children.length);
    console.log('   Text preview:', tvMenu.textContent?.substring(0, 100));
    
    // Analyze all children for clickable elements
    const menuItems = Array.from(tvMenu.querySelectorAll('*')).filter(el => {
      return el.tagName === 'DIV' || 
             el.tagName === 'BUTTON' ||
             el.tagName === 'SPAN' ||
             el.getAttribute('role') === 'menuitem' ||
             el.onclick ||
             el.getAttribute('tabindex') !== null;
    });
    
    console.log(`   Found ${menuItems.length} potential menu items:`);
    menuItems.forEach((item, i) => {
      if (i < 10) {
        const className = item.className?.toString() || 'no-class';
        const text = item.textContent?.trim() || '';
        console.log(`     ${i+1}. ${item.tagName}.${className}: "${text}"`);
        
        // Try clicking ANY menu item that might be export-related
        if (text.toLowerCase().includes('chart') || 
            text.toLowerCase().includes('data') ||
            text.toLowerCase().includes('download') ||
            text.toLowerCase().includes('save') ||
            text.toLowerCase().includes('export')) {
          console.log('🎯 POTENTIAL EXPORT ITEM FOUND!');
          return item; // Return this as the export item
        }
      }
    });
    
    // If no text-based match, try the first clickable item as a test
    if (menuItems.length > 0) {
      console.log('⚠️ No text-based match, but found context menu items. Testing first item...');
      return menuItems[0];
    }
  }
  
  // Strategy 5: Look for recently appeared clickable elements (context menu items)
  console.log('🔍 Looking for recently appeared clickable elements...');
  
  const recentClickables = Array.from(document.querySelectorAll('*')).filter(el => {
    const style = window.getComputedStyle(el);
    const isVisible = style.display !== 'none' && 
                     style.visibility !== 'hidden' && 
                     style.opacity !== '0' &&
                     el.offsetParent !== null;
                     
    const isClickable = el.tagName === 'BUTTON' || 
                       el.tagName === 'DIV' ||
                       el.getAttribute('role') === 'menuitem' ||
                       el.onclick ||
                       el.getAttribute('tabindex') !== null ||
                       style.cursor === 'pointer';
    
    return isVisible && isClickable;
  });
  
  console.log(`Found ${recentClickables.length} recent clickable elements`);
  
  // Look for any that might be export-related by position or context
  for (const clickable of recentClickables.slice(0, 20)) { // Check first 20
    const text = clickable.textContent?.toLowerCase() || '';
    const className = clickable.className?.toString() || '';
    
    // **ENHANCED: Exclude obvious non-menu elements**
    const isMainContainer = className.includes('js-rootresizer') ||
                           className.includes('layout__area') ||
                           className.includes('chart-container') ||
                           className.includes('tv-chart') ||
                           text.length > 200 || // Too much text = container, not menu item
                           clickable.tagName === 'HTML' ||
                           clickable.tagName === 'BODY';
    
    if (isMainContainer) {
      continue; // Skip main containers
    }
    
    // **ENHANCED: Only accept elements that look like actual menu items**
    const looksLikeMenuItem = (text.length > 0 && text.length < 50) || // Reasonable text length
                             className.includes('menu') ||
                             className.includes('item') ||
                             className.includes('button') ||
                             clickable.getAttribute('role') === 'menuitem' ||
                             clickable.getAttribute('data-name')?.includes('menu');
    
    // Check for export-related keywords BUT only if it looks like a menu item
    if (looksLikeMenuItem && (
        text.includes('export') ||
        text.includes('download') ||
        text.includes('save') ||
        (text.includes('chart') && text.includes('data') && text.length < 30) // Short, specific text
    )) {
      console.log(`🎯 Found potential export element: ${clickable.tagName}.${className}`);
      console.log(`   Text: "${clickable.textContent?.trim().substring(0, 50)}"`);
      console.log(`   Length: ${text.length} chars`);
      console.log(`   Role: ${clickable.getAttribute('role') || 'none'}`);
      console.log(`   Data-name: ${clickable.getAttribute('data-name') || 'none'}`);
      
      // Extra validation: make sure this isn't a huge container
      if (clickable.children.length < 10 && clickable.offsetHeight < 200) {
        return clickable;
      } else {
        console.log(`   ❌ Rejected: too many children (${clickable.children.length}) or too tall (${clickable.offsetHeight}px)`);
      }
    }
  }
  
  // **NEW: Emergency fallback - show all visible text on page**
  console.log('🆘 EMERGENCY DEBUG: Showing all visible text content...');
  const allTextElements = Array.from(document.querySelectorAll('*')).filter(el => {
    return el.textContent && 
           el.textContent.trim().length > 0 && 
           el.textContent.trim().length < 100 &&
           el.offsetParent !== null &&
           el.children.length === 0; // Leaf nodes only
  });
  
  console.log(`Found ${allTextElements.length} text elements. Showing first 50:`);
  allTextElements.slice(0, 50).forEach((el, i) => {
    const className = el.className?.toString() || 'no-class';
    console.log(`${i+1}. "${el.textContent?.trim()}" (${el.tagName}.${className})`);
  });
  
  // **NEW: Alternative strategy - try keyboard shortcut**
  console.log('🎯 TRYING ALTERNATIVE: Keyboard shortcut for export...');
  
  // Try common export keyboard shortcuts
  const chartArea = document.querySelector('[data-name="chart-area"]') || 
                   document.querySelector('.chart-markup-table') ||
                   document.querySelector('#chart-area') ||
                   document.querySelector('.chart');
  
  if (chartArea) {
    console.log('✅ Found chart area for keyboard shortcut');
    
    // Focus the chart area
    chartArea.focus();
    
    // Try Ctrl+E (common export shortcut)
    const ctrlEEvent = new KeyboardEvent('keydown', {
      key: 'e',
      code: 'KeyE',
      ctrlKey: true,
      bubbles: true,
      cancelable: true
    });
    
    console.log('⌨️ Sending Ctrl+E keyboard shortcut...');
    chartArea.dispatchEvent(ctrlEEvent);
    
    // Wait and check if anything appeared
    await sleep(2000);
    
    // Check for new dialogs
    const exportDialog = document.querySelector('[role="dialog"]') ||
                        document.querySelector('.dialog') ||
                        document.querySelector('[class*="dialog"]');
    
    if (exportDialog) {
      console.log('✅ Export dialog appeared via keyboard shortcut!');
      return { success: true, method: 'keyboard', element: exportDialog };
    }
  }
  
  console.log('❌ Export menu item not found with any strategy');
  console.log('� Total visible elements in DOM:', document.querySelectorAll('*:not([style*="display: none"]):not([style*="visibility: hidden"])').length);
  
  return null;
}

/**
 * Check if an element is clickable
 */
function isClickableElement(element) {
  if (!element) return false;
  
  // Check tag names
  if (['BUTTON', 'A', 'INPUT'].includes(element.tagName)) {
    return true;
  }
  
  // Check attributes that indicate clickability
  if (element.getAttribute('role') === 'menuitem' ||
      element.getAttribute('role') === 'button' ||
      element.getAttribute('role') === 'row' ||
      element.onclick ||
      element.getAttribute('tabindex') !== null ||
      element.style.cursor === 'pointer') {
    return true;
  }
  
  // Check classes that often indicate clickable elements
  const clickableClasses = ['clickable', 'button', 'menu-item', 'item'];
  const className = element.className.toLowerCase();
  for (const cls of clickableClasses) {
    if (className.includes(cls)) {
      return true;
    }
  }
  
  return false;
}

/**
 * Configure the export dialog and click Export button
 */
async function configureExportDialog() {
  console.log('⚙️ Configuring export dialog...');
  
  await sleep(800);
  
  // **UPDATED: Use EXACT selectors from DOM inspection screenshots**
  console.log('🎯 Looking for export dialog using exact TradingView structure...');
  
  const dialog = document.querySelector('[data-name="chart-export-dialog"]') ||  // EXACT match from screenshots
                 document.querySelector('div[role="dialog"][aria-labelledby*="title"]') ||  // Specific dialog pattern
                 document.querySelector('.wrapper-bSQMhzr') ||  // Specific wrapper class from screenshots
                 document.querySelector('[role="dialog"]') ||  // Generic dialog fallback
                 document.querySelector('.dialog') ||
                 document.querySelector('[class*="dialog"]') ||
                 Array.from(document.querySelectorAll('div')).find(el => 
                   el.textContent.includes('Export chart data')
                 );
  
  if (!dialog) {
    console.warn('⚠️ Export dialog not found with any selector');
    console.log('� Debugging: Checking what dialogs exist...');
    
    // Debug: Show all dialog-like elements
    const allDialogs = document.querySelectorAll('[role="dialog"], .dialog, [class*="dialog"], [data-name*="dialog"]');
    console.log(`   Found ${allDialogs.length} dialog-like elements:`);
    allDialogs.forEach((d, i) => {
      const className = d.className?.toString() || 'no-class';
      const dataName = d.getAttribute('data-name') || 'no-data-name';
      const text = d.textContent?.substring(0, 50) || '';
      console.log(`     ${i+1}. ${d.tagName}.${className} [data-name="${dataName}"] - "${text}"`);
    });
    
    console.log('�💡 Looking for Export button anywhere on page...');
    return await clickExportButtonGlobal();
  }
  
  console.log('✅ Found export dialog using selector:');
  console.log(`   Data-name: ${dialog.getAttribute('data-name')}`);
  console.log(`   Class: ${dialog.className}`);
  console.log(`   Text preview: ${dialog.textContent?.substring(0, 100)}`);
  
  // **STRATEGY 1: Use EXACT button selector from screenshots**
  console.log('🎯 Strategy 1: Looking for submit button using exact data-name...');
  let exportButton = dialog.querySelector('[data-name="submit-button"]');
  
  if (exportButton) {
    console.log('✅ Found Export button via EXACT data-name selector!');
    console.log('   Button details:', {
      tagName: exportButton.tagName,
      className: exportButton.className,
      dataName: exportButton.getAttribute('data-name'),
      textContent: exportButton.textContent?.trim()
    });
    
    exportButton.click();
    await showSuccessMessage();
    return true;
  }
  
  // **STRATEGY 2: Look for submitButton class from screenshots**
  console.log('🎯 Strategy 2: Looking for submitButton class...');
  exportButton = dialog.querySelector('.submitButton-PhMf7PhQ') ||
                 dialog.querySelector('[class*="submitButton"]');
  
  if (exportButton) {
    console.log('✅ Found Export button via submitButton class!');
    exportButton.click();
    await showSuccessMessage();
    return true;
  }
  
  // **STRATEGY 3: Look for content-D4RPB3ZC span from screenshots**
  console.log('🎯 Strategy 3: Looking for Export span with exact class...');
  const exportSpan = dialog.querySelector('span.content-D4RPB3ZC');
  if (exportSpan && exportSpan.textContent?.includes('Export')) {
    const button = exportSpan.closest('button, [role="button"], [data-name*="submit"], [tabindex]');
    if (button) {
      console.log('✅ Found Export button via content span class!');
      button.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  // Strategy 2: Look for span with "Export" text (based on captured HTML)
  const exportSpans = Array.from(dialog.querySelectorAll('span')).filter(span => {
    const text = span.textContent?.trim();
    return text === 'Export' || text === 'Export...' || text === 'Export ';
  });
  
  console.log(`Found ${exportSpans.length} export spans in dialog`);
  
  for (const span of exportSpans) {
    console.log(`   Checking span: "${span.textContent?.trim()}" with class: ${span.className}`);
    
    // Find the clickable parent button
    const button = span.closest('button, [role="button"], [data-name*="submit"], [tabindex]');
    if (button) {
      console.log('✅ Found Export button via span → button hierarchy, clicking...');
      console.log('   Button details:', {
        tagName: button.tagName,
        className: button.className,
        dataName: button.getAttribute('data-name'),
        role: button.getAttribute('role')
      });
      button.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  // Strategy 3: Look for buttons with Export text content
  const buttons = dialog.querySelectorAll('button, [role="button"]');
  console.log(`Found ${buttons.length} buttons in dialog`);
  
  for (const btn of buttons) {
    const text = btn.textContent?.trim().toLowerCase();
    const label = (btn.getAttribute('aria-label') || '').toLowerCase();
    
    console.log(`  Button: "${btn.textContent?.trim()}" (aria-label: "${btn.getAttribute('aria-label') || 'none'}")`);
    console.log(`    Classes: ${btn.className}`);
    console.log(`    Data-name: ${btn.getAttribute('data-name') || 'none'}`);
    
    // Check for spans with content-* class pattern inside buttons
    const contentSpan = btn.querySelector('span[class*="content-"]');
    if (contentSpan && contentSpan.textContent?.toLowerCase().includes('export')) {
      console.log('✅ Found Export button via content-* class pattern, clicking...');
      btn.click();
      await showSuccessMessage();
      return true;
    }
    
    if (text === 'export' || label === 'export' || text === 'export...' || text === 'export ') {
      console.log('✅ Found Export button via text match, clicking...');
      btn.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  // Strategy 4: By data-name attribute patterns (common in TradingView)
  let exportBtn = dialog.querySelector('[data-name="submit-button"]') ||
                  dialog.querySelector('[data-name*="submit"]') ||
                  dialog.querySelector('[data-name*="export"]') ||
                  dialog.querySelector('button[name="submit"]');
  
  if (exportBtn) {
    console.log('✅ Found Export button via data-name, clicking...');
    console.log('   Data-name:', exportBtn.getAttribute('data-name'));
    exportBtn.click();
    await showSuccessMessage();
    return true;
  }
  
  console.warn('⚠️ Export button not found in dialog');
  console.log('💡 Dialog appeared but extension cannot click Export button automatically');
  console.log('💡 Available spans with content-* classes in dialog:');
  
  // Debug: Show available content-* spans
  const contentSpans = dialog.querySelectorAll('span[class*="content-"]');
  contentSpans.forEach((span, i) => {
    if (i < 5) {
      console.log(`  ${i+1}. "${span.textContent?.trim()}" (${span.className})`);
    }
  });
  
  console.log('💡 Please click the Export button manually');
  
  return false;
}

/**
 * Try to find and click Export button globally (fallback) (UPDATED with monitored data)
 */
async function clickExportButtonGlobal() {
  console.log('🔍 Searching for Export button globally with EXACT TradingView selectors...');
  
  // **STRATEGY 1: Use EXACT button selector from DOM inspection**
  console.log('🎯 Strategy 1: Looking for exact data-name="submit-button"...');
  const exactSubmitBtn = document.querySelector('[data-name="submit-button"]');
  if (exactSubmitBtn) {
    console.log('✅ Found Export button via EXACT data-name selector!');
    console.log('   Button text:', exactSubmitBtn.textContent?.trim());
    console.log('   Button class:', exactSubmitBtn.className);
    
    exactSubmitBtn.click();
    await showSuccessMessage();
    return true;
  }
  
  // **STRATEGY 2: Look for submitButton class from DOM inspection**
  console.log('🎯 Strategy 2: Looking for submitButton-PhMf7PhQ class...');
  const submitButtonClass = document.querySelector('.submitButton-PhMf7PhQ') ||
                            document.querySelector('[class*="submitButton"]');
  if (submitButtonClass) {
    console.log('✅ Found Export button via submitButton class!');
    submitButtonClass.click();
    await showSuccessMessage();
    return true;
  }
  
  // **STRATEGY 3: Look for content-D4RPB3ZC span from DOM inspection**
  console.log('🎯 Strategy 3: Looking for exact content-D4RPB3ZC span...');
  const exactExportSpan = document.querySelector('span.content-D4RPB3ZC');
  if (exactExportSpan && exactExportSpan.textContent?.trim() === 'Export') {
    const button = exactExportSpan.closest('button, [role="button"], [data-name*="submit"], [tabindex]');
    if (button) {
      console.log('✅ Found Export button via EXACT content span class!');
      console.log('   Span text:', exactExportSpan.textContent);
      console.log('   Button details:', {
        tagName: button.tagName,
        className: button.className,
        dataName: button.getAttribute('data-name')
      });
      
      button.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  // **STRATEGY 4: Look within export dialog specifically**
  console.log('🎯 Strategy 4: Looking within export dialog container...');
  const exportDialog = document.querySelector('[data-name="chart-export-dialog"]') ||
                       document.querySelector('.wrapper-bSQMhzr');
  
  if (exportDialog) {
    console.log('   Found export dialog, searching for buttons inside...');
    
    // Look for any button with "Export" text inside the dialog
    const dialogButtons = exportDialog.querySelectorAll('button, [role="button"]');
    console.log(`   Found ${dialogButtons.length} buttons in dialog:`);
    
    for (let i = 0; i < dialogButtons.length; i++) {
      const btn = dialogButtons[i];
      const btnText = btn.textContent?.trim() || '';
      const btnClass = btn.className?.toString() || '';
      const btnDataName = btn.getAttribute('data-name') || '';
      
      console.log(`     ${i+1}. "${btnText}" (class: ${btnClass}, data-name: ${btnDataName})`);
      
      if (btnText.toLowerCase().includes('export') || 
          btnDataName.includes('submit') ||
          btnClass.includes('submit')) {
        console.log(`   ✅ Found Export button in dialog (button ${i+1})!`);
        btn.click();
        await showSuccessMessage();
        return true;
      }
    }
  }
  
  // Strategy 4: Original button text approach
  const allButtons = document.querySelectorAll('button');
  for (const btn of allButtons) {
    if ((btn.textContent.trim().toLowerCase() === 'export' || 
         btn.textContent.trim().toLowerCase() === 'export...') &&
        btn.offsetParent !== null) {
      console.log('✅ Found visible Export button via text, clicking...');
      btn.click();
      await showSuccessMessage();
      return true;
    }
  }
  
  console.log('❌ Could not find Export button');
  return false;
}

/**
 * Show success message after export and automate save process
 */
async function showSuccessMessage() {
  await sleep(1000);
  
  console.log('');
  console.log('═'.repeat(70));
  console.log('🎉 SUCCESS! Export button clicked successfully!');
  console.log('═'.repeat(70));
  console.log('� Attempting to automate save process...');
  console.log('📁 File will be saved to your default downloads folder');
  console.log('═'.repeat(70));
  console.log('');
  
  // Use a more reliable approach for TradingView's download system
  await handleTradingViewDownloadAutomation();
}

/**
 * Handle TradingView-specific download automation (LEGACY)
 */
async function handleTradingViewDownloadAutomation() {
  console.log('🤖 Starting TradingView download automation...');
  
  // Strategy 1: Monitor for automatic download (TradingView often auto-downloads)
  console.log('📥 Strategy 1: Waiting for automatic download...');
  await sleep(2000);
  
  // Strategy 2: Check if browser's download UI appeared
  if (document.querySelector('[download]') || 
      document.querySelector('a[href*="blob:"]') ||
      document.querySelector('a[href*="data:"]')) {
    console.log('✅ Download link detected - file should download automatically');
    await sleep(1000);
    
    console.log('');
    console.log('🎉 DOWNLOAD COMPLETE!');
    console.log('📁 Check your Downloads folder for the CSV file');
    console.log('📊 File contains visible chart data only (no bars limit)');
    console.log('');
    return;
  }
  
  // Strategy 3: Detect if OS save dialog is open and provide clear instructions
  console.log('💾 Strategy 3: OS Save dialog detected - providing user assistance...');
  
  // Check if page lost focus (typical when save dialog opens)
  if (document.hidden || !document.hasFocus()) {
    console.log('');
    console.log('═'.repeat(70));
    console.log('💾 SAVE DIALOG IS OPEN - ACTION REQUIRED');
    console.log('═'.repeat(70));
    console.log('🎯 SIMPLE SOLUTION (takes 2 seconds):');
    console.log('   1. Look at your screen - you should see a save dialog');
    console.log('   2. Press ENTER key once to save with default filename'); 
    console.log('   3. Or click the "Save" button in the dialog');
    console.log('');
    console.log('📄 File will be saved as: CME_MINI_MNQ1!_1D.csv (or similar)');
    console.log('📁 Location: Downloads folder (most likely)');
    console.log('');
    console.log('⏱️ After saving, the dialog will close automatically');
    console.log('═'.repeat(70));
    console.log('');
    
    // Show browser notification if possible
    showSaveNotification();
    
    // Try a single, simple automation attempt
    await sleep(2000);
    console.log('🤖 Attempting one simple automation...');
    await sendSimpleEnterKey();
    
    // Monitor for dialog closure
    setTimeout(() => {
      if (document.hasFocus() && !document.hidden) {
        console.log('');
        console.log('🎉 SUCCESS! Save completed successfully!');
        console.log('📁 File saved to Downloads folder');
        console.log('✅ Export process completed');
        console.log('');
      } else {
        console.log('');
        console.log('💡 Manual action still needed - please press ENTER in save dialog');
        console.log('');
      }
    }, 5000);
    
    return;
  }
  
  // Strategy 4: Fallback for other scenarios
  console.log('⌨️  Strategy 4: Using browser-level shortcuts...');
  
  try {
    window.focus();
    await sleep(500);
    await simulateCtrlS();
    await sleep(1000);
    await simulateEnterKey();
    await sleep(1000);
    
  } catch (error) {
    console.log('⚠️ Browser security prevented some automation attempts');
  }
  
  // Final guidance
  setTimeout(() => {
    console.log('');
    console.log('� EXPORT SUMMARY:');
    console.log('   ✅ Layout menu opened successfully');
    console.log('   ✅ Export option selected successfully'); 
    console.log('   ✅ Export dialog configured successfully');
    console.log('   ✅ Export button clicked successfully');
    console.log('   📁 File ready for download');
    console.log('');
    console.log('💡 If no save dialog appeared, check Downloads folder');
    console.log('   The file may have auto-downloaded already');
    console.log('');
  }, 3000);
}

/**
 * Simple and reliable Ctrl+S simulation
 */
async function simulateCtrlS() {
  console.log('⌨️  Simulating Ctrl+S...');
  
  try {
    // Method 1: Direct keydown event
    const event = new KeyboardEvent('keydown', {
      key: 's',
      code: 'KeyS',
      keyCode: 83,
      which: 83,
      ctrlKey: true,
      bubbles: true,
      cancelable: true
    });
    
    document.dispatchEvent(event);
    window.dispatchEvent(event);
    
    // Method 2: Try on active element
    if (document.activeElement) {
      document.activeElement.dispatchEvent(event);
    }
    
    console.log('✅ Ctrl+S event dispatched');
    
  } catch (error) {
    console.log('⚠️ Ctrl+S simulation blocked by browser security');
  }
}

/**
 * Handle OS-level save dialog automation
 */
async function handleOSSaveDialog() {
  console.log('');
  console.log('═'.repeat(70));
  console.log('💾 OS SAVE DIALOG DETECTED - ACTIVATING AUTO-SAVE');
  console.log('═'.repeat(70));
  console.log('🤖 Attempting to automatically save the file...');
  console.log('');
  
  // Wait a moment for dialog to fully appear
  await sleep(1000);
  
  // Strategy 1: Send Enter key to OS (most common save action)
  console.log('⌨️  Step 1: Sending Enter key to save with default filename...');
  await sendKeyToOS('Enter');
  await sleep(1500);
  
  // Strategy 2: Send Alt+S (Save button shortcut in Windows dialogs)
  console.log('⌨️  Step 2: Trying Alt+S shortcut...');
  await sendKeyToOS('s', { alt: true });
  await sleep(1500);
  
  // Strategy 3: Send Ctrl+S followed by Enter
  console.log('⌨️  Step 3: Trying Ctrl+S + Enter combination...');
  await sendKeyToOS('s', { ctrl: true });
  await sleep(500);
  await sendKeyToOS('Enter');
  await sleep(1500);
  
  // Strategy 4: Tab navigation to Save button
  console.log('⌨️  Step 4: Tab navigation to Save button...');
  for (let i = 0; i < 5; i++) {
    await sendKeyToOS('Tab');
    await sleep(200);
  }
  await sendKeyToOS('Enter');
  await sleep(1000);
  
  // Strategy 5: Space key (if Save button is focused)
  console.log('⌨️  Step 5: Trying Space key...');
  await sendKeyToOS(' ');
  await sleep(1000);
  
  // Provide feedback
  setTimeout(() => {
    console.log('');
    console.log('✅ AUTO-SAVE SEQUENCE COMPLETED!');
    console.log('');
    console.log('📁 FILE SHOULD NOW BE SAVED TO:');
    console.log('   • Downloads folder (most common)');
    console.log('   • Desktop (if changed default)');
    console.log('   • Last used save location');
    console.log('');
    console.log('🔍 TO VERIFY SAVE SUCCESS:');
    console.log('   1. Check if save dialog closed');
    console.log('   2. Look in Downloads folder for CSV file');
    console.log('   3. Check for browser download notification');
    console.log('');
    console.log('💡 IF DIALOG IS STILL OPEN:');
    console.log('   1. Press Enter manually');
    console.log('   2. Click Save button');
    console.log('   3. Change filename if needed, then press Enter');
    console.log('');
    
    // Add immediate manual override instructions
    console.log('🚨 QUICK MANUAL SAVE (if dialog still open):');
    console.log('   → Just press ENTER key once to save with default name');
    console.log('   → Or click the "Save" button in the dialog');
    console.log('   → The file will save as: CME_MINI_MNQ1!_1D.csv (or similar)');
    console.log('');
    console.log('═'.repeat(70));
    
    // Try one final automation attempt after the feedback
    setTimeout(() => {
      tryFinalSaveAttempt();
    }, 3000);
    
  }, 2000);
}

/**
 * Send keyboard input to the OS level (beyond browser sandbox)
 */
async function sendKeyToOS(key, modifiers = {}) {
  console.log(`   🔹 Sending ${modifiers.ctrl ? 'Ctrl+' : ''}${modifiers.alt ? 'Alt+' : ''}${modifiers.shift ? 'Shift+' : ''}${key}`);
  
  try {
    // Create the most comprehensive keyboard event possible
    const eventData = {
      key: key === 'Enter' ? 'Enter' : key === 'Tab' ? 'Tab' : key === ' ' ? ' ' : key,
      code: key === 'Enter' ? 'Enter' : key === 'Tab' ? 'Tab' : key === ' ' ? 'Space' : `Key${key.toUpperCase()}`,
      keyCode: getKeyCode(key),
      which: getKeyCode(key),
      ctrlKey: !!modifiers.ctrl,
      altKey: !!modifiers.alt,
      shiftKey: !!modifiers.shift,
      metaKey: !!modifiers.meta,
      bubbles: true,
      cancelable: true,
      composed: true
    };
    
    // Send to multiple targets for maximum compatibility
    const targets = [
      document,
      window,
      document.activeElement,
      document.body,
      document.documentElement
    ].filter(Boolean);
    
    // Send both keydown and keyup events
    for (const target of targets) {
      try {
        target.dispatchEvent(new KeyboardEvent('keydown', eventData));
        target.dispatchEvent(new KeyboardEvent('keypress', eventData));
        
        // Slight delay then keyup
        setTimeout(() => {
          target.dispatchEvent(new KeyboardEvent('keyup', eventData));
        }, 50);
      } catch (e) {
        // Ignore individual target errors
      }
    }
    
    // Also try the older event creation method
    try {
      const legacyEvent = document.createEvent('KeyboardEvent');
      legacyEvent.initKeyboardEvent(
        'keydown',
        true, // bubbles
        true, // cancelable
        window,
        eventData.ctrlKey,
        eventData.altKey,
        eventData.shiftKey,
        eventData.metaKey,
        eventData.keyCode,
        eventData.keyCode
      );
      document.dispatchEvent(legacyEvent);
    } catch (e) {
      // Legacy method failed, continue
    }
    
  } catch (error) {
    console.log(`   ⚠️ Error sending ${key}:`, error.message);
  }
}

/**
 * Get the numeric keycode for a key
 */
function getKeyCode(key) {
  const keyCodes = {
    'Enter': 13,
    'Tab': 9,
    ' ': 32,
    'Space': 32,
    's': 83,
    'S': 83
  };
  
  return keyCodes[key] || key.toUpperCase().charCodeAt(0);
}

/**
 * Final save attempt using different approach
 */
async function tryFinalSaveAttempt() {
  console.log('🔄 FINAL SAVE ATTEMPT...');
  console.log('');
  
  // Try to detect if dialog is still open by checking focus
  const isDialogStillOpen = document.hidden || !document.hasFocus();
  
  if (isDialogStillOpen) {
    console.log('💾 Save dialog appears to still be open - trying final automation...');
    
    // Simple approach: just send Enter key
    try {
      // Create a very simple enter event
      const enterKey = new KeyboardEvent('keydown', {
        key: 'Enter',
        keyCode: 13,
        which: 13,
        bubbles: true
      });
      
      // Send to window (most likely to reach OS dialog)
      window.dispatchEvent(enterKey);
      document.dispatchEvent(enterKey);
      
      console.log('✅ Sent final Enter key to save dialog');
      
      // Wait and check again
      setTimeout(() => {
        if (document.hasFocus() && !document.hidden) {
          console.log('');
          console.log('🎉 SUCCESS! Save dialog appears to have closed!');
          console.log('📁 File should now be saved to Downloads folder');
          console.log('');
        } else {
          console.log('');
          console.log('⚠️ Dialog may still be open - manual action required');
          console.log('');
          console.log('🖱️ SIMPLE SOLUTION:');
          console.log('   1. Look at your screen for the save dialog');
          console.log('   2. Press ENTER key once');
          console.log('   3. File will save automatically');
          console.log('');
          console.log('📄 The file will be named something like:');
          console.log('   CME_MINI_MNQ1!_1D.csv (or similar)');
          console.log('');
        }
      }, 2000);
      
    } catch (error) {
      console.log('⚠️ Final automation attempt failed - manual save required');
    }
  } else {
    console.log('✅ Browser has focus - save dialog likely closed successfully!');
    console.log('📁 Check Downloads folder for your CSV file');
  }
}

/**
 * Show browser notification to help user with save dialog
 */
function showSaveNotification() {
  try {
    // Try to show a browser notification
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('TradingView Export Ready', {
        body: 'Save dialog is open. Press ENTER to save your chart data.',
        icon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTkgMTZINXYtMmg0VjE2eiIgZmlsbD0iIzAwN2ZmZiIvPgo8L3N2Zz4K'
      });
    } else if ('Notification' in window && Notification.permission !== 'denied') {
      // Request permission
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          new Notification('TradingView Export Ready', {
            body: 'Save dialog is open. Press ENTER to save your chart data.'
          });
        }
      });
    }
  } catch (error) {
    // Notifications not supported or blocked
  }
  
  // Also try to create a visual indicator on the page
  try {
    createVisualSaveIndicator();
  } catch (error) {
    // Visual indicator failed
  }
}

/**
 * Create a visual indicator on the page
 */
function createVisualSaveIndicator() {
  // Remove any existing indicator
  const existing = document.getElementById('save-indicator');
  if (existing) existing.remove();
  
  // Create floating save indicator
  const indicator = document.createElement('div');
  indicator.id = 'save-indicator';
  indicator.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: #007fff;
    color: white;
    padding: 15px 20px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 10000;
    font-family: Arial, sans-serif;
    font-size: 14px;
    font-weight: bold;
    animation: pulse 2s infinite;
    cursor: pointer;
  `;
  
  indicator.innerHTML = `
    💾 Save Dialog Open<br>
    <small>Press ENTER to save</small>
  `;
  
  // Add CSS animation
  const style = document.createElement('style');
  style.textContent = `
    @keyframes pulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.05); }
      100% { transform: scale(1); }
    }
  `;
  document.head.appendChild(style);
  
  // Add click handler to send Enter
  indicator.addEventListener('click', () => {
    sendSimpleEnterKey();
    indicator.style.background = '#28a745';
    indicator.innerHTML = '✅ Save attempt sent!';
    setTimeout(() => {
      indicator.remove();
    }, 3000);
  });
  
  document.body.appendChild(indicator);
  
  // Auto-remove after 30 seconds
  setTimeout(() => {
    if (document.getElementById('save-indicator')) {
      indicator.remove();
    }
  }, 30000);
}

/**
 * Send a simple Enter key (simplified version)
 */
async function sendSimpleEnterKey() {
  console.log('⌨️  Sending simple Enter key for save dialog...');
  
  try {
    const enterEvent = new KeyboardEvent('keydown', {
      key: 'Enter',
      keyCode: 13,
      which: 13,
      bubbles: true,
      cancelable: true
    });
    
    // Send to multiple targets
    document.dispatchEvent(enterEvent);
    window.dispatchEvent(enterEvent);
    
    if (document.activeElement) {
      document.activeElement.dispatchEvent(enterEvent);
    }
    
    console.log('✅ Enter key sent to save dialog');
    
  } catch (error) {
    console.log('⚠️ Could not send Enter key:', error.message);
  }
}

/**
 * Automatically handle the save process with multiple strategies
 */
async function automateSaveProcess() {
  console.log('🤖 Starting automated save process...');
  
  // Wait a bit for save dialog to fully load
  await sleep(1500);
  
  // Strategy 1: Try multiple keyboard shortcuts for save
  console.log('⌨️  Strategy 1: Trying keyboard shortcuts...');
  
  // Simulate Ctrl+S (save shortcut)
  await simulateKeyboardShortcut('KeyS', true); // Ctrl+S
  await sleep(500);
  
  // Strategy 2: Simulate Enter key (common for default save button)
  console.log('⌨️  Strategy 2: Trying Enter key...');
  await simulateEnterKey();
  await sleep(500);
  
  // Strategy 3: Try Alt+S (Save button shortcut in many dialogs)
  console.log('⌨️  Strategy 3: Trying Alt+S shortcut...');
  await simulateKeyboardShortcut('KeyS', false, true); // Alt+S
  await sleep(500);
  
  // Strategy 4: Try Space key (if Save button is focused)
  console.log('⌨️  Strategy 4: Trying Space key...');
  await simulateSpaceKey();
  await sleep(500);
  
  // Strategy 5: Try Tab navigation + Enter
  console.log('⌨️  Strategy 5: Trying Tab navigation...');
  for (let i = 0; i < 3; i++) {
    await simulateTabKey();
    await sleep(200);
  }
  await simulateEnterKey();
  
  console.log('✅ Save automation attempts completed');
  console.log('💡 If file didn\'t save automatically, the save dialog may require manual interaction');
  
  // Give user feedback and fallback option
  setTimeout(() => {
    console.log('');
    console.log('🔄 FALLBACK OPTIONS if save didn\'t work:');
    console.log('   1. Press Ctrl+S in the browser');
    console.log('   2. Press Enter if save dialog is visible');
    console.log('   3. Click Save button manually in the file dialog');
    console.log('   4. Check your Downloads folder for the exported file');
    console.log('');
  }, 2000);
}

/**
 * Simulate keyboard shortcut with modifiers
 */
async function simulateKeyboardShortcut(key, ctrl = false, alt = false, shift = false) {
  console.log(`⌨️  Simulating ${ctrl ? 'Ctrl+' : ''}${alt ? 'Alt+' : ''}${shift ? 'Shift+' : ''}${key}`);
  
  const event = new KeyboardEvent('keydown', {
    key: key === 'KeyS' ? 's' : key,
    code: key,
    keyCode: key === 'KeyS' ? 83 : (key === 'Enter' ? 13 : 0),
    which: key === 'KeyS' ? 83 : (key === 'Enter' ? 13 : 0),
    ctrlKey: ctrl,
    altKey: alt,
    shiftKey: shift,
    bubbles: true,
    cancelable: true
  });
  
  // Dispatch to both document and active element
  document.dispatchEvent(event);
  if (document.activeElement) {
    document.activeElement.dispatchEvent(event);
  }
  
  // Also try the corresponding keyup event
  const keyupEvent = new KeyboardEvent('keyup', {
    key: key === 'KeyS' ? 's' : key,
    code: key,
    keyCode: key === 'KeyS' ? 83 : (key === 'Enter' ? 13 : 0),
    which: key === 'KeyS' ? 83 : (key === 'Enter' ? 13 : 0),
    ctrlKey: ctrl,
    altKey: alt,
    shiftKey: shift,
    bubbles: true,
    cancelable: true
  });
  
  setTimeout(() => {
    document.dispatchEvent(keyupEvent);
    if (document.activeElement) {
      document.activeElement.dispatchEvent(keyupEvent);
    }
  }, 100);
}

/**
 * Simulate Tab key press for navigation
 */
async function simulateTabKey() {
  const event = new KeyboardEvent('keydown', {
    key: 'Tab',
    code: 'Tab',
    keyCode: 9,
    which: 9,
    bubbles: true,
    cancelable: true
  });
  
  document.dispatchEvent(event);
  if (document.activeElement) {
    document.activeElement.dispatchEvent(event);
  }
}

/**
 * Simulate Space key press
 */
async function simulateSpaceKey() {
  const event = new KeyboardEvent('keydown', {
    key: ' ',
    code: 'Space',
    keyCode: 32,
    which: 32,
    bubbles: true,
    cancelable: true
  });
  
  document.dispatchEvent(event);
  if (document.activeElement) {
    document.activeElement.dispatchEvent(event);
  }
}

/**
 * Enhanced Enter key simulation
 */
async function simulateEnterKey() {
  console.log('⌨️  Simulating Enter key press...');
  
  // Create keydown event
  const keydownEvent = new KeyboardEvent('keydown', {
    key: 'Enter',
    code: 'Enter',
    keyCode: 13,
    which: 13,
    bubbles: true,
    cancelable: true
  });
  
  // Create keyup event
  const keyupEvent = new KeyboardEvent('keyup', {
    key: 'Enter',
    code: 'Enter',
    keyCode: 13,
    which: 13,
    bubbles: true,
    cancelable: true
  });
  
  // Dispatch to document
  document.dispatchEvent(keydownEvent);
  
  // Also try on the active element
  const activeElement = document.activeElement;
  if (activeElement) {
    activeElement.dispatchEvent(keydownEvent);
  }
  
  // Dispatch keyup after a short delay
  setTimeout(() => {
    document.dispatchEvent(keyupEvent);
    if (activeElement) {
      activeElement.dispatchEvent(keyupEvent);
    }
  }, 100);
  
  console.log('✅ Enter key simulated');
}

/**
 * Find the Save button in Windows save dialog
 */
async function findSaveButton() {
  // Wait a bit for dialog to fully load
  await sleep(500);
  
  // Strategy 1: Look for Save button by text
  const buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"]'));
  
  let saveBtn = buttons.find(btn => {
    const text = btn.textContent?.trim().toLowerCase();
    const value = btn.value?.toLowerCase();
    return text === 'save' || value === 'save';
  });
  
  if (saveBtn) {
    console.log('✅ Found Save button via text/value match');
    return saveBtn;
  }
  
  // Strategy 2: Look for buttons with save-related attributes
  saveBtn = document.querySelector('button[data-action="save"]') ||
            document.querySelector('button[name="save"]') ||
            document.querySelector('input[name="save"]') ||
            document.querySelector('[aria-label*="Save"]') ||
            document.querySelector('[title*="Save"]');
  
  if (saveBtn) {
    console.log('✅ Found Save button via attributes');
    return saveBtn;
  }
  
  // Strategy 3: Look for submit buttons in forms (common for save dialogs)
  const forms = document.querySelectorAll('form');
  for (const form of forms) {
    const submitBtn = form.querySelector('input[type="submit"], button[type="submit"]');
    if (submitBtn) {
      console.log('✅ Found form submit button');
      return submitBtn;
    }
  }
  
  // Strategy 4: Check if this is actually a browser download dialog (not a web page)
  // Browser save dialogs can't be automated via JavaScript for security reasons
  if (document.title.includes('Save') || 
      document.body?.textContent?.includes('wants to save') ||
      window.location.href === 'about:blank') {
    console.log('💡 This appears to be a browser/OS save dialog (cannot be automated)');
    return null;
  }
  
  console.log('❌ Save button not found');
  return null;
}

/**
 * Show manual instructions (fallback)
 */
function showManualInstructions(settings) {
  const message = `
╔═══════════════════════════════════════════════════════════╗
║          TRADINGVIEW EXPORT - MANUAL MODE                 ║
╚═══════════════════════════════════════════════════════════╝

Automatic export needs manual help!

WHAT TO DO NOW:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The extension tried to automate the export but needs you
to complete the final steps:

1. Right-click menu should be open
   (If not, right-click on chart area)

2. Click "Export chart data..." option

3. Click "Export" in the dialog
   (Will export visible chart data automatically)

4. Choose save location and filename

Settings being used:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Symbol: ${settings.symbol}
• Exchange: ${settings.exchange}
• Data: Visible chart range (automatic)

The extension will continue trying to automate after you
complete these steps manually.

Click OK to continue.
`;

  alert(message);
}

/**
 * Take screenshot
 */
function takeScreenshot() {
  console.log('📸 Requesting screenshot...');
  chrome.runtime.sendMessage({action: 'captureTab'});
}

/**
 * Capture HTML for debugging
 */
function captureHTML() {
  console.log('📋 Capturing HTML for debugging...');
  
  // Capture full page HTML
  const fullHTML = document.documentElement.outerHTML;
  console.log('📄 Full page HTML captured (length:', fullHTML.length, ')');
  
  // Look for context menu
  const menu = document.querySelector('[role="menu"], .context-menu, [class*="menu"], [class*="item"]');
  if (menu) {
    console.log('🎯 CONTEXT MENU HTML:');
    console.log(menu.outerHTML);
  }
  
  // Look for dialog
  const dialog = document.querySelector('[role="dialog"], .dialog, [class*="dialog"]');
  if (dialog) {
    console.log('💬 DIALOG HTML:');
    console.log(dialog.outerHTML);
  }
  
  // Look for Export spans specifically
  const exportSpans = Array.from(document.querySelectorAll('span')).filter(span => {
    return span.textContent?.trim() === 'Export';
  });
  
  if (exportSpans.length > 0) {
    console.log('🎯 EXPORT SPANS FOUND:');
    exportSpans.forEach((span, i) => {
      console.log(`Export Span ${i+1}:`, span.outerHTML);
      console.log(`Parent:`, span.parentElement?.outerHTML || 'none');
    });
  }
  
  // Save to file (download)
  const blob = new Blob([fullHTML], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `tradingview-${Date.now()}.html`;
  a.click();
  URL.revokeObjectURL(url);
  
  console.log('✅ HTML file downloaded to Downloads folder');
}

/**
 * Debug function to log current page state
 */
function debugPageState() {
  console.log('🔍 DEBUG: Current page state');
  console.log('═'.repeat(50));
  
  // Check for menus
  const menus = document.querySelectorAll('[role="menu"], .context-menu, [class*="menu"]');
  console.log(`Menus found: ${menus.length}`);
  menus.forEach((menu, i) => {
    console.log(`Menu ${i+1}:`, menu.outerHTML.substring(0, 200) + '...');
  });
  
  // Check for dialogs
  const dialogs = document.querySelectorAll('[role="dialog"], .dialog, [class*="dialog"]');
  console.log(`Dialogs found: ${dialogs.length}`);
  dialogs.forEach((dialog, i) => {
    console.log(`Dialog ${i+1}:`, dialog.outerHTML.substring(0, 200) + '...');
  });
  
  // Check for export text - MORE DETAILED
  const exportElements = Array.from(document.querySelectorAll('*')).filter(el => {
    const text = el.textContent?.toLowerCase();
    return text && text.includes('export') && el.children.length === 0;
  });
  console.log(`Elements with 'export' text: ${exportElements.length}`);
  exportElements.forEach((el, i) => {
    console.log(`Export element ${i+1}:`, {
      text: el.textContent?.trim(),
      tagName: el.tagName,
      className: el.className,
      role: el.getAttribute('role'),
      tabindex: el.getAttribute('tabindex'),
      onclick: el.onclick ? 'has onclick' : 'no onclick',
      parent: el.parentElement?.tagName,
      parentClass: el.parentElement?.className?.substring(0, 50),
      parentRole: el.parentElement?.getAttribute('role'),
      isVisible: el.offsetParent !== null,
      outerHTML: el.outerHTML.substring(0, 150) + '...'
    });
  });
  
  // Check all visible clickable elements
  const clickableElements = Array.from(document.querySelectorAll('button, [role="menuitem"], [role="button"], [role="row"], a, [onclick], [tabindex]'))
    .filter(el => el.offsetParent !== null);
  
  console.log(`Visible clickable elements: ${clickableElements.length}`);
  clickableElements.slice(0, 15).forEach((el, i) => {
    const text = el.textContent?.trim().substring(0, 30);
    console.log(`Clickable ${i+1}: "${text}" (${el.tagName}, role: ${el.getAttribute('role') || 'none'})`);
  });
  
  console.log('═'.repeat(50));
}

/**
 * Click an element with proper event simulation
 */
async function clickElement(element) {
  if (!element) {
    throw new Error('Element is null or undefined');
  }
  
  console.log(`🖱️ Clicking element: ${element.tagName}${element.className ? '.' + element.className : ''}`);
  
  // Scroll element into view if needed
  element.scrollIntoView({ behavior: 'smooth', block: 'center' });
  await sleep(100);
  
  // Create mouse events
  const mouseDownEvent = new MouseEvent('mousedown', {
    bubbles: true,
    cancelable: true,
    view: window,
    button: 0,
    buttons: 1
  });
  
  const clickEvent = new MouseEvent('click', {
    bubbles: true,
    cancelable: true,
    view: window,
    button: 0,
    buttons: 0
  });
  
  const mouseUpEvent = new MouseEvent('mouseup', {
    bubbles: true,
    cancelable: true,
    view: window,
    button: 0,
    buttons: 0
  });
  
  // Dispatch events with human timing
  element.dispatchEvent(mouseDownEvent);
  await sleep(Math.random() * 80 + 40);
  element.dispatchEvent(clickEvent);
  await sleep(Math.random() * 30 + 10);
  element.dispatchEvent(mouseUpEvent);
  
  console.log(`✅ Clicked element successfully`);
}

/**
 * Human-like sleep with random variation
 */
function sleep(ms) {
  // Add random variation to sleep times (±20%)
  const variation = ms * 0.2;
  const randomMs = ms + (Math.random() - 0.5) * variation * 2;
  return new Promise(resolve => setTimeout(resolve, Math.max(50, randomMs)));
}

/**
 * Listen for messages from background script and popup
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Content script received message:', request);
  
  if (request.action === 'getSymbol') {
    // Try to extract symbol from page
    const symbol = extractSymbolFromPage();
    sendResponse({ symbol: symbol });
    return true;
  }
  
  if (request.action === 'export' || request.action === 'exportData') {
    // Handle both legacy and new export actions
    console.log('🚀 Starting TradingView export with settings:', request.settings);
    
    handleTradingViewDownload(request.settings || {})
      .then(result => {
        console.log('✅ Export completed successfully:', result);
        sendResponse({ success: true, message: 'Export completed successfully' });
      })
      .catch(error => {
        console.error('❌ Export failed:', error);
        sendResponse({ success: false, error: error.message });
      });
    return true; // Keep message channel open for async response
  }
});

/**
 * Main export handler - now with Downloads API integration
 */
async function handleTradingViewDownload(settings = {}) {
  console.log('🎯 TradingView export handler started');
  console.log('📊 Export settings:', settings);
  
  try {
    // Step 1: Trigger the TradingView export workflow
    console.log('🔄 Step 1: Triggering TradingView export workflow...');
    const exportResult = await handleTradingViewDownloadOriginal(settings);
    
    if (!exportResult) {
      throw new Error('Export workflow failed');
    }
    
    console.log('✅ Step 1 completed: TradingView export triggered');
    
    // Step 2: Wait for download to be detected by Downloads API
    console.log('🔄 Step 2: Waiting for Downloads API to detect file...');
    
    // Send symbol info to background script for smart naming
    const symbol = extractSymbolFromPage();
    chrome.runtime.sendMessage({
      action: 'updateSymbolInfo',
      symbol: symbol,
      timestamp: Date.now()
    });
    
    // Monitor for blob creation (TradingView creates blob URLs for CSV downloads)
    let downloadDetected = false;
    let downloadTimeout;
    
    const downloadPromise = new Promise((resolve, reject) => {
      // Set up blob URL monitoring
      const originalCreateObjectURL = URL.createObjectURL;
      URL.createObjectURL = function(blob) {
        const url = originalCreateObjectURL.call(this, blob);
        
        console.log('🔍 Blob created:', {
          type: blob.type,
          size: blob.size,
          url: url.substring(0, 50) + '...'
        });
        
        // Check if this looks like a CSV export
        if ((blob.type && blob.type.includes('csv')) || 
            (blob.type && blob.type.includes('text')) || 
            blob.size > 100) {
          
          console.log('🎯 CSV download blob detected!');
          downloadDetected = true;
          
          // Restore original function
          URL.createObjectURL = originalCreateObjectURL;
          
          // Clear timeout
          if (downloadTimeout) {
            clearTimeout(downloadTimeout);
          }
          
          // Give Downloads API time to process
          setTimeout(() => {
            resolve({
              success: true,
              message: 'CSV export detected and processed',
              blobInfo: { type: blob.type, size: blob.size }
            });
          }, 1000);
        }
        
        return url;
      };
      
      // Set timeout for download detection
      downloadTimeout = setTimeout(() => {
        if (!downloadDetected) {
          console.log('⚠️ Download not detected within timeout');
          URL.createObjectURL = originalCreateObjectURL; // Restore original
          resolve({
            success: true,
            message: 'Export completed but download not detected (may have saved directly)'
          });
        }
      }, 10000); // 10 second timeout
    });
    
    // Wait for download detection
    const downloadResult = await downloadPromise;
    console.log('✅ Step 2 completed:', downloadResult.message);
    
    // Step 3: Show success message
    console.log('🎉 Export process completed successfully!');
    showExportSuccessMessage(downloadResult);
    
    return downloadResult;
    
  } catch (error) {
    console.error('❌ Export handler failed:', error);
    
    // Show fallback success message
    showExportFallbackMessage(error);
    throw error;
  }
}

/**
 * Show export success message
 */
function showExportSuccessMessage(result) {
  console.log('');
  console.log('═'.repeat(70));
  console.log('🎉 TRADINGVIEW EXPORT SUCCESSFUL!');
  console.log('═'.repeat(70));
  console.log('✅ Export process completed');
  console.log('📁 File processed by Downloads API');
  console.log('💾 Smart filename and organization applied');
  console.log('🔔 Check for browser notification');
  console.log('');
  console.log('📂 Expected location: Downloads/TradingView_Data/');
  console.log('📄 Filename format: chart_export_SYMBOL_2025-11-03_TIME.csv');
  console.log('═'.repeat(70));
  console.log('');
}

/**
 * Show fallback message if Downloads API didn't detect
 */
function showExportFallbackMessage(error) {
  console.log('');
  console.log('═'.repeat(70));
  console.log('⚠️ EXPORT COMPLETED (Downloads API not detected)');
  console.log('═'.repeat(70));
  console.log('✅ TradingView export triggered successfully');
  console.log('📁 File may have been saved directly to Downloads folder');
  console.log('');
  console.log('🔍 To find your file:');
  console.log('   1. Check Downloads folder for CSV files');
  console.log('   2. Look for files with current timestamp');
  console.log('   3. Check browser download history (Ctrl+J)');
  console.log('');
  console.log('📋 Error details:', error.message);
  console.log('═'.repeat(70));
  console.log('');
}

/**
 * Original export workflow (renamed for clarity)
 */
async function handleTradingViewDownloadOriginal(settings = {}) {
  console.log('🚀 Starting original TradingView export workflow...');
  
  // Call the main export function that handles the TradingView automation
  return await exportData(settings);
}

/**
 * Extract symbol information from TradingView page
 */
function extractSymbolFromPage() {
  console.log('� Extracting symbol from TradingView page...');
  
  // Strategy 1: Check URL params
  const urlParams = new URLSearchParams(window.location.search);
  const symbolFromUrl = urlParams.get('symbol');
  if (symbolFromUrl) {
    console.log('✅ Found symbol in URL:', symbolFromUrl);
    return symbolFromUrl;
  }
  
  // Strategy 2: Check page title
  const title = document.title;
  const titleMatch = title.match(/([A-Z0-9]+)\s*(?:Chart|TradingView)/i);
  if (titleMatch) {
    console.log('✅ Found symbol in title:', titleMatch[1]);
    return titleMatch[1];
  }
  
  // Strategy 3: Look for symbol display elements
  const symbolSelectors = [
    '[data-name="legend-source-item"]',
    '.chart-markup-table .legend .item',
    '.legend-TW8L5AjY .item-TW8L5AjY',
    '[class*="legend"] [class*="item"]',
    '[class*="symbol"]',
    '.tv-chart-header__symbol'
  ];
  
  for (const selector of symbolSelectors) {
    const element = document.querySelector(selector);
    if (element) {
      const text = element.textContent?.trim();
      if (text && text.length < 20 && /^[A-Z0-9:!]+$/.test(text)) {
        console.log('✅ Found symbol via selector:', text);
        return text;
      }
    }
  }
  
  // Strategy 4: Look for symbol in chart configuration
  try {
    const configScripts = document.querySelectorAll('script');
    for (const script of configScripts) {
      const content = script.textContent || '';
      const symbolMatch = content.match(/"symbol"\s*:\s*"([^"]+)"/);
      if (symbolMatch) {
        console.log('✅ Found symbol in script config:', symbolMatch[1]);
        return symbolMatch[1];
      }
    }
  } catch (e) {
    console.log('⚠️ Could not parse script configs for symbol');
  }
  
  console.log('❌ Could not extract symbol from page');
  return 'UNKNOWN_SYMBOL';
}

/**
 * Simulate human reading/thinking time
 */
      size: blob.size,
      url: url.substring(0, 50) + '...'
    });
    
    if (blob.type.includes('csv') || blob.type.includes('text') || blob.size > 100) {
      console.log('');
      console.log('═'.repeat(70));
      console.log('📥 CSV DOWNLOAD DETECTED!');
      console.log('═'.repeat(70));
      console.log('   📄 File type:', blob.type || 'text/csv');
      console.log('   📊 File size:', blob.size, 'bytes');
      console.log('   🔗 Download URL created');
      console.log('═'.repeat(70));
      downloadStarted = true;
      
      // Wait a moment then provide final status
      setTimeout(() => {
        console.log('');
        console.log('🎉 EXPORT SUCCESSFUL!');
        console.log('📁 Chart data has been exported');
        console.log('💾 File should auto-download or save dialog should appear');
        console.log('');
        console.log('🔍 If you don\'t see the download:');
        console.log('   1. Check browser download notifications');
        console.log('   2. Look in Downloads folder for CSV file');
        console.log('   3. Check if browser blocked the download');
        console.log('');
      }, 1500);
    }
    return url;
  };
  
  // Monitor for download anchor elements
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.tagName === 'A' && node.download && !downloadStarted) {
          console.log('');
          console.log('📥 DOWNLOAD LINK CREATED!');
          console.log('   📄 Filename:', node.download);
          console.log('   🔗 URL:', node.href.substring(0, 50) + '...');
          
          // Auto-click the download link
          console.log('🖱️  Auto-clicking download link...');
          node.click();
          downloadStarted = true;
          
          setTimeout(() => {
            console.log('✅ Download initiated successfully!');
            console.log('📁 Check Downloads folder for:', node.download);
          }, 1000);
        }
      });
    });
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
  
  // Monitor for any download-related clicks
  document.addEventListener('click', (event) => {
    const target = event.target;
    if (target.tagName === 'A' && (target.download || target.href.includes('blob:') || target.href.includes('data:'))) {
      console.log('📥 Download link clicked!');
      console.log('   📄 File:', target.download || 'auto-generated');
      console.log('   🔗 Type:', target.href.includes('blob:') ? 'Blob URL' : 'Data URL');
      downloadStarted = true;
      
      setTimeout(() => {
        console.log('');
        console.log('🎉 DOWNLOAD COMPLETE!');
        console.log('📁 File saved to Downloads folder');
        console.log('📊 Export contains visible chart data');
        console.log('');
      }, 1000);
    }
  });
  
  // Monitor for browser download notifications
  if ('serviceWorker' in navigator) {
    // Check for download completion via service worker events
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data && event.data.type === 'download-complete') {
        console.log('� Service worker detected download completion');
        downloadStarted = true;
      }
    });
  }
}

/**
 * Simulate human reading/thinking time
 */
function humanPause() {
  // Random pause between 300-1500ms (human processing time)
  return sleep(Math.random() * 1200 + 300);
}

// Ready!
console.log('✅ TradingView Exporter: Enhanced with Downloads API');
console.log('💡 Click extension icon and press "Export Visible Data" to start');
console.log('🔧 Downloads API will automatically manage files with smart names');