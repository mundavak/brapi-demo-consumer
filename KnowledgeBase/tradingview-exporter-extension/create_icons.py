"""
Generate placeholder icons for TradingView Exporter extension
Run this to create the required icon files
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Icon sizes needed
SIZES = [16, 48, 128]

# Output directory
OUTPUT_DIR = r"F:\TradingAgent\deaProjects\brapi-demo-consumer\KnowledgeBase\tradingview-exporter-extension\icons"

# Create icons directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_icon(size):
    """Create a simple colored icon"""
    
    # Create image with purple gradient background
    img = Image.new('RGB', (size, size), '#667eea')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple chart-like pattern
    # Draw bars
    bar_width = size // 8
    colors = ['#764ba2', '#9061f9', '#667eea', '#764ba2']
    
    for i in range(4):
        x = (i + 1) * (size // 5)
        height = (i + 2) * (size // 6)
        y = size - height
        
        draw.rectangle(
            [x - bar_width//2, y, x + bar_width//2, size],
            fill=colors[i]
        )
    
    # Add text if size is large enough
    if size >= 48:
        try:
            # Try to use a nice font
            font = ImageFont.truetype("arial.ttf", size // 4)
        except:
            # Fallback to default
            font = ImageFont.load_default()
        
        text = "TV"
        
        # Get text size
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center text
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        # Draw text with shadow
        draw.text((x + 2, y + 2), text, fill='#000000', font=font)
        draw.text((x, y), text, fill='#ffffff', font=font)
    
    # Save icon
    filepath = os.path.join(OUTPUT_DIR, f"icon{size}.png")
    img.save(filepath, 'PNG')
    print(f"✅ Created: {filepath}")

def main():
    print("="*60)
    print("Creating TradingView Exporter Icons")
    print("="*60)
    
    try:
        for size in SIZES:
            create_icon(size)
        
        print("\n" + "="*60)
        print("✅ All icons created successfully!")
        print("="*60)
        print(f"\nIcons saved to: {OUTPUT_DIR}")
        print("\nNext steps:")
        print("1. Go to chrome://extensions/")
        print("2. Enable 'Developer mode'")
        print("3. Click 'Load unpacked'")
        print("4. Select folder:")
        print(f"   {os.path.dirname(OUTPUT_DIR)}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nIf PIL/Pillow not installed, run:")
        print("  pip install Pillow")

if __name__ == "__main__":
    main()