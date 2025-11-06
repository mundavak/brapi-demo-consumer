/**
 * Debug Context Menu - Manual DOM Analysis Tool
 * 
 * How to use:
 * 1. Open browser console on TradingView
 * 2. Copy and paste this entire script
 * 3. Right-click on chart
 * 4. Quickly run: analyzeContextMenu()
 * 5. Copy the output to help debug automation
 */

function analyzeContextMenu() {
  console.log('🔍 CONTEXT MENU ANALYSIS STARTING...');
  console.log('=====================================');
  
  // Find all visible elements that appeared recently
  const allElements = Array.from(document.querySelectorAll('*'));
  const visibleElements = allElements.filter(el => {
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && 
           style.visibility !== 'hidden' && 
           style.opacity !== '0' &&
           el.offsetParent !== null;
  });
  
  console.log(`Total visible elements: ${visibleElements.length}`);
  
  // Look for potential menu containers
  const menuContainers = visibleElements.filter(el => {
    const tag = el.tagName.toLowerCase();
    const classes = (el.className?.toString() || '').toLowerCase(); // Fixed: handle non-string className
    const role = el.getAttribute('role') || '';
    
    return (
      // By tag
      tag === 'div' || tag === 'ul' || tag === 'menu' ||
      // By class keywords
      classes.includes('menu') ||
      classes.includes('popup') ||
      classes.includes('context') ||
      classes.includes('dropdown') ||
      classes.includes('overlay') ||
      // By role
      role.includes('menu') ||
      // By having multiple children (likely menu items)
      (el.children.length >= 3 && el.children.length <= 20)
    );
  });
  
  console.log(`\n🎯 POTENTIAL MENU CONTAINERS (${menuContainers.length}):`);
  console.log('=================================================');
  
  menuContainers.forEach((container, i) => {
    const className = container.className?.toString() || 'no-class'; // Fixed: safe className access
    console.log(`\n${i + 1}. Container: ${container.tagName}.${className}`);
    console.log(`   ID: ${container.id || 'none'}`);
    console.log(`   Role: ${container.getAttribute('role') || 'none'}`);
    console.log(`   Children: ${container.children.length}`);
    console.log(`   Position: ${window.getComputedStyle(container).position}`);
    console.log(`   Z-index: ${window.getComputedStyle(container).zIndex}`);
    
    // Analyze children for export-related text
    const children = Array.from(container.children);
    const exportChildren = children.filter(child => {
      const text = child.textContent?.toLowerCase() || '';
      return text.includes('export') || text.includes('download') || text.includes('save');
    });
    
    if (exportChildren.length > 0) {
      console.log(`   🎯 EXPORT-RELATED CHILDREN (${exportChildren.length}):`);
      exportChildren.forEach((child, j) => {
        const childClass = child.className?.toString() || 'no-class'; // Fixed: safe className access
        console.log(`      ${j + 1}. ${child.tagName}.${childClass}`);
        console.log(`         Text: "${child.textContent?.trim()}"`);
        console.log(`         Role: ${child.getAttribute('role') || 'none'}`);
        
        // Look for spans inside
        const spans = child.querySelectorAll('span');
        if (spans.length > 0) {
          console.log(`         Spans (${spans.length}):`);
          spans.forEach((span, k) => {
            const spanClass = span.className?.toString() || 'no-class'; // Fixed: safe className access
            console.log(`           ${k + 1}. span.${spanClass}: "${span.textContent?.trim()}"`);
          });
        }
      });
    }
  });
  
  // Search specifically for spans with export text
  console.log(`\n🔍 ALL SPANS WITH EXPORT TEXT:`);
  console.log('================================');
  
  const exportSpans = visibleElements.filter(el => {
    return el.tagName === 'SPAN' && 
           el.textContent?.toLowerCase().includes('export');
  });
  
  exportSpans.forEach((span, i) => {
    const spanClass = span.className?.toString() || 'no-class'; // Fixed: safe className access
    const parentClass = span.parentElement?.className?.toString() || 'no-class'; // Fixed: safe className access
    const grandparentClass = span.parentElement?.parentElement?.className?.toString() || 'no-class'; // Fixed: safe className access
    
    console.log(`${i + 1}. span.${spanClass}: "${span.textContent?.trim()}"`);
    console.log(`   Parent: ${span.parentElement?.tagName}.${parentClass}`);
    console.log(`   Grandparent: ${span.parentElement?.parentElement?.tagName}.${grandparentClass}`);
  });
  
  // Look for elements with specific classes that might be TradingView menus
  console.log(`\n🔍 TRADINGVIEW-STYLE ELEMENTS:`);
  console.log('==============================');
  
  const tvElements = visibleElements.filter(el => {
    const classes = (el.className?.toString() || '').toLowerCase(); // Fixed: handle non-string className
    return classes.includes('label-') || 
           classes.includes('content-') ||
           classes.includes('item-') ||
           classes.includes('menu-') ||
           classes.includes('popup-');
  });
  
  tvElements.forEach((el, i) => {
    if (i < 20) { // Limit output
      const className = el.className?.toString() || 'no-class'; // Fixed: safe className access
      console.log(`${i + 1}. ${el.tagName}.${className}: "${el.textContent?.trim().substring(0, 50)}"`);
    }
  });
  
  console.log('\n🔍 ANALYSIS COMPLETE');
  console.log('===================');
  console.log('💡 Look for export-related elements in the output above');
  console.log('💡 Pay attention to the exact class names and DOM structure');
  console.log('💡 Copy this output to help update the automation selectors');
}

// Auto-run in 3 seconds to give time to right-click
console.log('🎯 Context Menu Debug Tool Loaded');
console.log('📋 Instructions:');
console.log('   1. Right-click on the TradingView chart');
console.log('   2. Quickly run: analyzeContextMenu()');
console.log('   3. Copy the output for debugging');
console.log('');
console.log('⏱️  Auto-running in 5 seconds... Right-click NOW!');

setTimeout(() => {
  console.log('🚀 AUTO-RUNNING CONTEXT MENU ANALYSIS...');
  analyzeContextMenu();
}, 5000);