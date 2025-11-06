/**
 * Save Helper Script
 * This script can be injected to help with OS save dialog automation
 */

// Function to send a simple Enter key that might work with OS dialogs
function sendSimpleEnter() {
  console.log('🔥 Sending simple Enter key...');
  
  // Method 1: Direct key event
  const event = new KeyboardEvent('keydown', {
    key: 'Enter',
    keyCode: 13,
    which: 13
  });
  
  document.dispatchEvent(event);
  window.dispatchEvent(event);
  
  // Method 2: Try to click any visible Save button
  const saveButtons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
  for (const btn of saveButtons) {
    const text = btn.textContent || btn.value || '';
    if (text.toLowerCase().includes('save') || text.toLowerCase().includes('ok')) {
      console.log('🖱️ Found potential save button, clicking:', text);
      btn.click();
      break;
    }
  }
  
  console.log('✅ Simple save attempt completed');
}

// Export for use in content script
if (typeof window !== 'undefined') {
  window.sendSimpleEnter = sendSimpleEnter;
}