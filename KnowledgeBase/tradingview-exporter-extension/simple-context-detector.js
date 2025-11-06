/**
 * SIMPLE CONTEXT MENU DETECTOR
 * 
 * Usage:
 * 1. Open TradingView in browser
 * 2. Open browser console (F12)
 * 3. Copy and paste this code
 * 4. Right-click on chart
 * 5. Immediately run: detectContextMenu()
 */

function detectContextMenu() {
  console.log('🔍 DETECTING CONTEXT MENU...');
  console.log('==============================');
  
  // Look for elements with high z-index (likely popups/menus)
  const allElements = Array.from(document.querySelectorAll('*'));
  const highZIndexElements = allElements.filter(el => {
    const style = window.getComputedStyle(el);
    const zIndex = parseInt(style.zIndex) || 0;
    return zIndex > 1000 && 
           style.display !== 'none' &&
           style.visibility !== 'hidden' &&
           el.offsetParent !== null;
  });
  
  console.log(`Found ${highZIndexElements.length} high z-index elements:`);
  
  highZIndexElements.forEach((el, i) => {
    const style = window.getComputedStyle(el);
    const className = el.className?.toString() || 'no-class';
    
    console.log(`${i+1}. ${el.tagName}.${className}`);
    console.log(`   Z-index: ${style.zIndex}`);
    console.log(`   Position: ${style.position}`);
    console.log(`   Children: ${el.children.length}`);
    console.log(`   Text: "${el.textContent?.trim().substring(0, 100)}"`);
    
    // Check if this might be a context menu
    if (el.children.length > 1 && el.children.length < 20) {
      console.log(`   🎯 POTENTIAL CONTEXT MENU - analyzing children:`);
      
      Array.from(el.children).forEach((child, j) => {
        const childClass = child.className?.toString() || 'no-class';
        const childText = child.textContent?.trim() || '';
        console.log(`      ${j+1}. ${child.tagName}.${childClass}: "${childText}"`);
        
        // Look for export-related terms
        if (childText.toLowerCase().includes('export') ||
            childText.toLowerCase().includes('download') ||
            childText.toLowerCase().includes('save') ||
            childText.toLowerCase().includes('chart') ||
            childText.toLowerCase().includes('data')) {
          console.log(`         ⭐ EXPORT-RELATED TEXT FOUND!`);
        }
      });
    }
    console.log('');
  });
  
  // Also look for recently added DOM elements
  console.log('\n🔍 CHECKING FOR RECENTLY ADDED ELEMENTS...');
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === 1 && node.children && node.children.length > 0) {
          console.log(`🆕 Added element: ${node.tagName}.${node.className}`);
          console.log(`   Text: "${node.textContent?.trim().substring(0, 100)}"`);
        }
      });
    });
  });
  
  observer.observe(document.body, { childList: true, subtree: true });
  
  // Stop observing after 5 seconds
  setTimeout(() => {
    observer.disconnect();
    console.log('🔍 Mutation observation stopped');
  }, 5000);
  
  console.log('🎯 DETECTION COMPLETE');
  console.log('💡 Right-click on chart now and check the output above!');
}

// Auto-detect in 3 seconds
console.log('🎯 Context Menu Detector Loaded');
console.log('📋 Right-click on chart, then run: detectContextMenu()');
console.log('⏱️  Or wait 3 seconds for auto-detection...');

setTimeout(() => {
  console.log('🚀 AUTO-RUNNING CONTEXT MENU DETECTION...');
  detectContextMenu();
}, 3000);