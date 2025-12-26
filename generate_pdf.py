#!/usr/bin/env python3
"""
Generate PDF documentation from markdown file.
"""
import subprocess
import sys

def create_pdf_simple():
    """Create PDF using simple text formatting"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        # Read markdown content
        with open('Google_Ads_API_Design_Documentation.md', 'r') as f:
            content = f.read()

        # Create PDF
        pdf_file = 'Google_Ads_API_Design_Documentation.pdf'
        doc = SimpleDocTemplate(pdf_file, pagesize=letter,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)

        # Container for the 'Flowable' objects
        elements = []

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='#2c3e50',
            spaceAfter=30,
            alignment=TA_CENTER
        )
        heading1_style = ParagraphStyle(
            'CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            textColor='#2c3e50',
            spaceAfter=12,
            spaceBefore=16
        )
        heading2_style = ParagraphStyle(
            'CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            textColor='#34495e',
            spaceAfter=10,
            spaceBefore=12
        )
        heading3_style = ParagraphStyle(
            'CustomHeading3',
            parent=styles['Heading3'],
            fontSize=12,
            textColor='#555555',
            spaceAfter=8,
            spaceBefore=10
        )
        body_style = styles['BodyText']
        code_style = ParagraphStyle(
            'Code',
            parent=styles['Code'],
            fontSize=9,
            leftIndent=20,
            spaceBefore=6,
            spaceAfter=6
        )

        # Process markdown content line by line
        lines = content.split('\n')
        i = 0
        in_code_block = False
        code_block = []

        while i < len(lines):
            line = lines[i]

            # Handle code blocks
            if line.startswith('```'):
                if in_code_block:
                    # End of code block
                    code_text = '\n'.join(code_block)
                    elements.append(Preformatted(code_text, code_style))
                    elements.append(Spacer(1, 0.2*inch))
                    code_block = []
                    in_code_block = False
                else:
                    # Start of code block
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                code_block.append(line)
                i += 1
                continue

            # Handle headings
            if line.startswith('# '):
                text = line[2:].strip()
                if i == 0:  # First heading is title
                    elements.append(Paragraph(text, title_style))
                else:
                    elements.append(Paragraph(text, heading1_style))
                elements.append(Spacer(1, 0.15*inch))
            elif line.startswith('## '):
                text = line[3:].strip()
                elements.append(Paragraph(text, heading1_style))
                elements.append(Spacer(1, 0.12*inch))
            elif line.startswith('### '):
                text = line[4:].strip()
                elements.append(Paragraph(text, heading2_style))
                elements.append(Spacer(1, 0.1*inch))
            elif line.startswith('#### '):
                text = line[5:].strip()
                elements.append(Paragraph(text, heading3_style))
                elements.append(Spacer(1, 0.08*inch))
            elif line.startswith('- ') or line.startswith('* '):
                # Bullet point
                text = '• ' + line[2:].strip()
                elements.append(Paragraph(text, body_style))
            elif line.startswith('---'):
                # Horizontal rule
                elements.append(Spacer(1, 0.2*inch))
            elif line.strip().startswith('**') and line.strip().endswith('**'):
                # Bold text as subheading
                text = line.strip()[2:-2]
                elements.append(Paragraph(f'<b>{text}</b>', body_style))
            elif line.strip() and not line.startswith('#'):
                # Regular paragraph
                elements.append(Paragraph(line.strip(), body_style))
                elements.append(Spacer(1, 0.1*inch))
            elif not line.strip():
                # Empty line
                elements.append(Spacer(1, 0.05*inch))

            i += 1

        # Build PDF
        doc.build(elements)
        print(f"✓ PDF created successfully: {pdf_file}")
        return True

    except ImportError:
        print("reportlab not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
        print("Please run the script again.")
        return False
    except Exception as e:
        print(f"Error creating PDF: {e}")
        return False

if __name__ == "__main__":
    create_pdf_simple()
