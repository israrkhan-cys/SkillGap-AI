from flask import Flask, render_template, request, jsonify, send_file
import os
from groq import Groq
from werkzeug.utils import secure_filename
import PyPDF2
import docx
from dotenv import load_dotenv
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Groq client
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Store analysis results in session (in production, use proper session management)
analysis_cache = {}

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    text = ""
    try:
        doc = docx.Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX: {e}")
    return text

def extract_text_from_file(file_path, filename):
    """Extract text based on file extension"""
    extension = filename.rsplit('.', 1)[1].lower()
    
    if extension == 'pdf':
        return extract_text_from_pdf(file_path)
    elif extension == 'docx':
        return extract_text_from_docx(file_path)
    elif extension == 'txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    return ""

def analyze_cv_with_groq(cv_text, target_role="General Professional Role"):
    """Send CV to Groq API for analysis with target role"""
    try:
        prompt = f"""You are a career development advisor specializing in skill assessment and career growth.

Analyze the following CV/resume for the target role: {target_role}

Return clearly in exactly this format:

**MISSING SKILLS:**
Start with the 2-3 most CRITICAL skills for {target_role}. Mark them like this:
🔴 PRIORITY 1: [Skill name] - [Brief description] | Learn: [Resource type like YouTube/Coursera/FreeCodeCamp/Udemy]
🔴 PRIORITY 2: [Skill name] - [Brief description] | Learn: [Resource type]
🟡 PRIORITY 3 (if applicable): [Skill name] - [Brief description] | Learn: [Resource type]

Then list 4-5 additional important skills:
- [Skill name] - [Brief description] | Learn: [Resource type]
- [Skill name] - [Brief description] | Learn: [Resource type]

**CURRENT SKILLS IDENTIFIED:**
List 3-5 skills that the candidate already has:
- [Skill name]
- [Skill name]
- [Skill name]

**LEARNING ROADMAP:**
Step 1: [First skill to learn] - [Why it matters for {target_role} and estimated time]
Step 2: [Second skill to learn] - [Why it matters for {target_role} and estimated time]
Step 3: [Third skill to learn] - [Why it matters for {target_role} and estimated time]
Step 4: [Fourth skill to learn] - [Why it matters for {target_role} and estimated time]
Step 5: [Fifth skill to learn] - [Why it matters for {target_role} and estimated time]

**JOB READINESS SCORE:**
Score: [X]/100

**EXPLANATION:**
[2-3 sentences evaluating readiness specifically for {target_role}, highlighting relevant strengths and critical gaps]

Focus your analysis on skills and experience that matter for a {target_role} position. Consider both technical and non-technical competencies. For each missing skill, suggest which free learning platform would be best (YouTube, Coursera, FreeCodeCamp, Udemy, LinkedIn Learning, Codecademy, etc).

CV/Resume:
{cv_text}
"""

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert career counselor and technical recruiter specializing in skill gap analysis for tech professionals. Provide actionable, specific, and realistic feedback."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1500
        )
        
        return chat_completion.choices[0].message.content
    
    except Exception as e:
        return f"Error analyzing CV: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    cv_text = ""
    target_role = request.form.get('target_role', '')
    custom_role = request.form.get('custom_role', '').strip()
    
    # Use custom role if provided, otherwise use dropdown selection
    if custom_role:
        target_role = custom_role
    elif not target_role or target_role == "General Tech Role":
        target_role = "General Professional Role"
    
    # Check if file was uploaded
    if 'file' in request.files and request.files['file'].filename != '':
        file = request.files['file']
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Extract text from file
            cv_text = extract_text_from_file(file_path, filename)
            
            # Clean up uploaded file
            os.remove(file_path)
        else:
            return jsonify({'error': 'Invalid file type. Please upload PDF, DOCX, or TXT files.'}), 400
    
    # Check if text was pasted
    elif 'cv_text' in request.form and request.form['cv_text'].strip():
        cv_text = request.form['cv_text']
    
    else:
        return jsonify({'error': 'Please provide a CV either by uploading a file or pasting text.'}), 400
    
    # Validate CV text
    if not cv_text or len(cv_text.strip()) < 50:
        return jsonify({'error': 'CV text is too short. Please provide a complete CV.'}), 400
    
    # Analyze with Groq, passing target role
    analysis = analyze_cv_with_groq(cv_text, target_role)
    
    # Store analysis in cache for PDF download
    session_id = str(datetime.now().timestamp())
    analysis_cache[session_id] = {
        'analysis': analysis,
        'target_role': target_role,
        'timestamp': datetime.now()
    }
    
    return jsonify({'analysis': analysis, 'session_id': session_id})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'SkillGap AI is running!'})

def generate_pdf_report(analysis_text, target_role):
    """Generate a PDF report from the analysis"""
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=10,
        alignment=1  # Center
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#764ba2'),
        spaceAfter=8,
        spaceBefore=8
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=12
    )
    
    # Title
    elements.append(Paragraph("SkillGap AI - Skill Gap Analysis Report", title_style))
    elements.append(Paragraph(f"Target Role: <b>{target_role}</b>", heading_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", normal_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Divider
    divider_data = [['']]
    divider_table = Table(divider_data, colWidths=[7.5*inch])
    divider_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 2, colors.HexColor('#667eea')),
    ]))
    elements.append(divider_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Parse and format analysis content
    lines = analysis_text.split('\n')
    
    for line in lines:
        if line.strip() == '':
            elements.append(Spacer(1, 0.05*inch))
        elif line.strip().startswith('**') and line.strip().endswith('**'):
            # Section heading
            heading_text = line.strip().replace('**', '')
            elements.append(Paragraph(heading_text, heading_style))
        elif line.strip().startswith('-') or line.strip().startswith('•'):
            # Bullet point
            bullet_text = line.strip().lstrip('-•').strip()
            elements.append(Paragraph(f"• {bullet_text}", normal_style))
        elif line.strip().startswith('Step'):
            # Learning roadmap step
            elements.append(Paragraph(line.strip(), ParagraphStyle(
                'StepStyle',
                parent=normal_style,
                leftIndent=0.2*inch,
                backgroundColor=colors.HexColor('#f3f0ff'),
                borderPadding=5
            )))
        elif line.strip().startswith('Score:'):
            # Score line - make it bold
            elements.append(Paragraph(f"<b>{line.strip()}</b>", ParagraphStyle(
                'ScoreStyle',
                parent=normal_style,
                fontSize=12,
                textColor=colors.HexColor('#764ba2')
            )))
        else:
            elements.append(Paragraph(line.strip(), normal_style))
    
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Made with SkillGap AI - From Resume to Roadmap in Seconds", 
                            ParagraphStyle(
                                'Footer',
                                parent=styles['Normal'],
                                fontSize=9,
                                textColor=colors.grey,
                                alignment=1
                            )))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/download-pdf/<session_id>')
def download_pdf(session_id):
    """Download analysis report as PDF"""
    if session_id not in analysis_cache:
        return jsonify({'error': 'Report not found. Please analyze a CV first.'}), 404
    
    cached_data = analysis_cache[session_id]
    analysis_text = cached_data['analysis']
    target_role = cached_data['target_role']
    
    # Generate PDF
    pdf_buffer = generate_pdf_report(analysis_text, target_role)
    
    # Create filename
    filename = f"SkillGap_Analysis_{target_role.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
