import os
import io
import sys
import logging
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, FrameBreak, Frame, KeepInFrame

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class CustomDocTemplate(SimpleDocTemplate):
    """
    Custom document template that extends SimpleDocTemplate with additional functionality.
    """
    def __init__(self, filename, **kw):
        SimpleDocTemplate.__init__(self, filename, **kw)
        self.frames = []
        
    def handle_frameBegin(self, frame=None, **kwargs):
        """Override to handle frame beginning"""
        if frame is not None:
            self.frame = frame
            return SimpleDocTemplate.handle_frameBegin(self, frame, **kwargs)
        elif hasattr(self, 'frame') and self.frame is not None:
            # Use the existing frame if available
            return SimpleDocTemplate.handle_frameBegin(self, self.frame, **kwargs)
        else:
            # Handle the case when frame is not provided
            return SimpleDocTemplate.handle_frameBegin(self, **kwargs)

def create_score_graph(feedback_data):
    """
    Create a bar graph image for the feedback data.
    """
    # Prepare data
    references = []
    totals = []
    for data in feedback_data.values():
        ref = data.get('reference', data.get('staff_name', ''))
        references.append(ref)
        # Calculate total score out of 100
        totals.append((sum(data['scores']) / 10) * 10)
    
    # Create the plot with optimal dimensions
    plt.rcParams['figure.dpi'] = 300
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(references, totals, color='#007bff')
    
    # Remove axis labels, keep only the grid and ticks
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_title('')
    ax.set_ylim(0, 100)
    
    plt.xticks(fontsize=9)
    plt.yticks(fontsize=9)
    
    # Add value labels on top of each bar
    for bar, total in zip(bars, totals):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, height,
               f'{total:.1f}',
               ha='center', va='bottom',
               fontsize=9)
    
    # Add grid for better readability
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    plt.close(fig)
    buf.seek(0)
    return buf

class FooterCanvas:
    def __init__(self, canvas, doc):
        self.canvas = canvas
        self.doc = doc
        
    def draw_footer(self):
        # Draw watermark at the bottom of the page
        self.canvas.saveState()
        watermark1 = "Form No. AC 14b      Rev.No. 00      Effective Date: 15/12/2017"
        watermark2_center = "© GENREC AI"
        watermark2_right = "VSB ENGINEERING COLLEGE/CSBS/BATCH 2023-2027"
        self.canvas.setFont("Helvetica", 7)
        self.canvas.setFillColor(colors.gray)
        
        # Left aligned text with margin
        self.canvas.drawString(25, 20, watermark1)
        
        # Center aligned text
        self.canvas.drawCentredString(self.doc.pagesize[0]/2, 20, watermark2_center)
        
        # Right aligned text with margin
        right_text_width = self.canvas.stringWidth(watermark2_right, "Helvetica", 7)
        self.canvas.drawString(self.doc.pagesize[0] - right_text_width - 25, 20, watermark2_right)
        
        self.canvas.restoreState()


def generate_feedback_report(academic_year, branch, semester, year, feedback_data):
    """Generate a single-page PDF report with prominent graph."""
    filename = f"feedback_report_{branch}_Semester {semester}.pdf"
    filepath = os.path.abspath(filename)
    logger.info(f"Generating report: {filename}")
    
    # Create a CustomDocTemplate
    doc = CustomDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=40  # Increased bottom margin for watermark
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=12,
        alignment=1,
        spaceAfter=2
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubTitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        spaceAfter=2
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=1,
        spaceAfter=4
    )
    
    question_style = ParagraphStyle(
        'QuestionStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=9,
        leftIndent=0
    )
    
    reference_style = ParagraphStyle(
        'ReferenceStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=9,
        leftIndent=20
    )

    reference_title_style = ParagraphStyle(
        'ReferenceTitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=10,
        fontName='Helvetica-Bold'
    )
    
    # Document elements
    elements = []

    elements.append(Paragraph("V.S.B. ENGINEERING COLLEGE, KARUR", title_style))
    elements.append(Paragraph("(An Autonomous Institution)", subtitle_style))
    elements.append(Paragraph("STUDENT'S FEEDBACK ON COURSE DELIVERY", subtitle_style))

    academic_info = f"Academic year: {academic_year}    Branch: {branch}    Semester: {semester}    Year: {year}"
    elements.append(Paragraph(academic_info, info_style))
    elements.append(Spacer(1, 3))

    # Create feedback data table
    table_data = [
        ['Staff Name', 'Subject'] + [f'Q{i}' for i in range(1, 11)] + ['Total']
    ]

    for key, data in feedback_data.items():
        scores = data['scores']
        # Calculate total as average * 10 (to get percentage)
        total = (sum(scores)/10) * 10
        row = [
            data['staff_name'],
            data['subject']
        ] + [f"{score:.1f}" for score in scores] + [f"{total:.1f}"]
        table_data.append(row)

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 5))

    # Add graph
    graph_buffer = create_score_graph(feedback_data)
    img = Image(graph_buffer)
    img.drawWidth = A4[0] - 50
    img.drawHeight = 2.5 * inch
    elements.append(img)
    elements.append(Spacer(1, 5))

    # Add references
    elements.append(Paragraph("References:", reference_title_style))
    elements.append(Spacer(1, 2))
    
    for key, data in feedback_data.items():
        reference_line = f"{data['reference']}: {data['staff_name']} - {data['subject']}"
        elements.append(Paragraph(reference_line, reference_style))
    
    elements.append(Spacer(1, 3))
    
    # Add questions with reduced spacing
    questions_text = [
        "Q1: How is the faculty's approach?",
        "Q2: How has the faculty prepared for the classes?",
        "Q3: Does the faculty inform you about your expected competencies, course outcomes?",
        "Q4: How often does the faculty illustrate the concepts through examples and practical applications?",
        "Q5: Whether faculty covers syllabus in time?",
        "Q6: Do you agree that the faculty teaches content beyond syllabus?",
        "Q7: How does the faculty communicate?",
        "Q8: Whether faculty returns answer scripts in time and produce helpful comments?",
        "Q9: How does the faculty identify your strengths and encourage you with high level of challenges?",
        "Q10: How does the faculty counsel & encourage the Students?"
    ]
    
    for question in questions_text:
        elements.append(Paragraph(question, question_style))
    
    # Add three lines of space before signature section
    elements.append(Spacer(1, 20))
    elements.append(Spacer(1, 20))
    elements.append(Spacer(1, 20))
    
    # Add signature section
    signature_table = Table(
        [["Class Advisor", "HOD", "Principal"]],
        colWidths=[doc.width/3.0]*3,
        style=TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('GRID', (0, 0), (-1, -1), 0, colors.white),
        ])
    )
    elements.append(signature_table)
    
    try:
        # Add the footer to each page
        def footer_func(canvas, doc):
            FooterCanvas(canvas, doc).draw_footer()
            
        # Build the document with the footer function
        doc.build(elements, onFirstPage=footer_func, onLaterPages=footer_func)
        logger.info(f"Report saved: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}")
        raise

if __name__ == "__main__":
    department = "Computer Science and Business Systems"
    semester = 4
    logger.info(f"Processing {department} - Semester {semester}")
    
    def read_feedback_data(department, semester):
        return {
            "staff1_subject1": {
                "reference": "S1",
                "staff_name": "Dr. Smith",
                "subject": "Mathematics",
                "scores": [8.5, 9.0, 8.0, 7.5, 9.0, 8.0, 8.5, 9.0, 8.0, 8.5]
            },
            "staff2_subject1": {
                "reference": "S2",
                "staff_name": "Prof. Johnson",
                "subject": "Physics",
                "scores": [7.5, 8.0, 7.0, 8.5, 8.0, 7.5, 7.0, 8.0, 7.5, 8.0]
            }
        }
    
    feedback_data = read_feedback_data(department, semester)
    
    filepath = generate_feedback_report(
        academic_year="2024-25",
        branch=department,
        semester=semester,
        year="II",
        feedback_data=feedback_data
    )
    logger.info(f"Report ready: {filepath}")
