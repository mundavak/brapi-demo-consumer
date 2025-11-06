#!/usr/bin/env python3
"""
Convert the installation guide to PDF format
Requires: pip install markdown pdfkit weasyprint
Alternative: Use pandoc if available
"""

import os
import sys
from pathlib import Path

def convert_with_pandoc():
    """Convert using pandoc (recommended)"""
    input_file = "MCP_PDF_Reader_Installation_Guide.md"
    output_file = "MCP_PDF_Reader_Installation_Guide.pdf"
    
    cmd = f'pandoc "{input_file}" -o "{output_file}" --pdf-engine=wkhtmltopdf --css=style.css'
    
    print(f"Converting {input_file} to PDF...")
    result = os.system(cmd)
    
    if result == 0:
        print(f"✅ PDF created: {output_file}")
    else:
        print("❌ Pandoc conversion failed. Trying alternative method...")
        return False
    return True

def convert_with_weasyprint():
    """Convert using WeasyPrint"""
    try:
        import markdown
        from weasyprint import HTML, CSS
        
        input_file = "MCP_PDF_Reader_Installation_Guide.md"
        output_file = "MCP_PDF_Reader_Installation_Guide.pdf"
        
        # Read markdown
        with open(input_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Convert to HTML
        html_content = markdown.markdown(md_content, extensions=['codehilite', 'tables', 'toc'])
        
        # Add CSS styling
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>MCP PDF Reader Installation Guide</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                h2 {{ color: #34495e; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }}
                h3 {{ color: #7f8c8d; }}
                code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px; font-family: Consolas, monospace; }}
                pre {{ background-color: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                blockquote {{ border-left: 4px solid #3498db; margin: 0; padding-left: 20px; color: #7f8c8d; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; }}
                .success {{ background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; }}
                .error {{ background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; }}
            </style>
        </head>
        <body>
        {html_content}
        </body>
        </html>
        """
        
        # Convert to PDF
        HTML(string=full_html).write_pdf(output_file)
        print(f"✅ PDF created: {output_file}")
        return True
        
    except ImportError:
        print("❌ Required packages not installed. Install with:")
        print("pip install markdown weasyprint")
        return False
    except Exception as e:
        print(f"❌ WeasyPrint conversion failed: {e}")
        return False

def convert_with_pdfkit():
    """Convert using pdfkit (requires wkhtmltopdf)"""
    try:
        import markdown
        import pdfkit
        
        input_file = "MCP_PDF_Reader_Installation_Guide.md"
        output_file = "MCP_PDF_Reader_Installation_Guide.pdf"
        
        # Read and convert markdown
        with open(input_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        html_content = markdown.markdown(md_content, extensions=['codehilite', 'tables', 'toc'])
        
        # PDF options
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None
        }
        
        pdfkit.from_string(html_content, output_file, options=options)
        print(f"✅ PDF created: {output_file}")
        return True
        
    except ImportError:
        print("❌ Required packages not installed. Install with:")
        print("pip install markdown pdfkit")
        print("Also install wkhtmltopdf: https://wkhtmltopdf.org/downloads.html")
        return False
    except Exception as e:
        print(f"❌ PDFKit conversion failed: {e}")
        return False

def main():
    print("MCP PDF Reader Installation Guide - PDF Converter")
    print("=" * 60)
    
    # Check if markdown file exists
    if not os.path.exists("MCP_PDF_Reader_Installation_Guide.md"):
        print("❌ Installation guide markdown file not found!")
        return
    
    # Try conversion methods in order of preference
    methods = [
        ("Pandoc", convert_with_pandoc),
        ("WeasyPrint", convert_with_weasyprint), 
        ("PDFKit", convert_with_pdfkit)
    ]
    
    for method_name, method_func in methods:
        print(f"\nTrying {method_name}...")
        if method_func():
            print(f"\n✅ Successfully created PDF using {method_name}")
            break
    else:
        print("\n❌ All PDF conversion methods failed.")
        print("\nManual alternatives:")
        print("1. Use online markdown to PDF converter")
        print("2. Open the .md file in VS Code and print to PDF")
        print("3. Install pandoc: https://pandoc.org/installing.html")

if __name__ == "__main__":
    main()