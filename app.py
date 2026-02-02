from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
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
import json

# Set UTF-8 encoding for the entire application
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    import io
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Force UTF-8 for all string operations
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['JSON_AS_ASCII'] = False  # Ensure JSON responses use UTF-8
app.config['JSON_SORT_KEYS'] = False

# Helper to create safe JSON responses
def safe_jsonify(data):
    """Create JSON response with proper UTF-8 encoding"""
    # Ensure all strings in data are UTF-8 safe
    def encode_dict(obj):
        if isinstance(obj, dict):
            return {k: encode_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [encode_dict(item) for item in obj]
        elif isinstance(obj, str):
            return safe_encode(obj)
        else:
            return obj
    
    safe_data = encode_dict(data)
    # Use json.dumps with ensure_ascii=False for proper UTF-8
    response_str = json.dumps(safe_data, ensure_ascii=False)
    response = app.response_class(
        response=response_str,
        status=200,
        mimetype='application/json; charset=utf-8'
    )
    return response

def safe_jsonify_error(data, status_code=500):
    """Create error JSON response with proper UTF-8 encoding"""
    def encode_dict(obj):
        if isinstance(obj, dict):
            return {k: encode_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [encode_dict(item) for item in obj]
        elif isinstance(obj, str):
            return safe_encode(obj)
        else:
            return obj
    
    safe_data = encode_dict(data)
    response_str = json.dumps(safe_data, ensure_ascii=False)
    response = app.response_class(
        response=response_str,
        status=status_code,
        mimetype='application/json; charset=utf-8'
    )
    return response

# Ensure UTF-8 response encoding
@app.after_request
def set_utf8_response(response):
    if response.content_type is None or 'application/json' in response.content_type:
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
    elif response.content_type and 'text' in response.content_type:
        response.headers['Content-Type'] = response.content_type.split(';')[0] + '; charset=utf-8'
    return response

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Groq client with validation
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY or GROQ_API_KEY == 'your_groq_api_key_here':
    print("WARNING: GROQ_API_KEY not set or using default value!")
    print("Please set your GROQ_API_KEY in the .env file")
    print("Get your API key from: https://console.groq.com/keys")
    client = None
else:
    try:
        # Ensure API key is ASCII-safe (remove any non-ASCII characters)
        GROQ_API_KEY = GROQ_API_KEY.encode('ascii', errors='ignore').decode('ascii')
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"ERROR: Failed to initialize Groq client: {e}")
        client = None

# Store analysis results in session (in production, use proper session management)
analysis_cache = {}

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_encode(text):
    """Safely encode any text to UTF-8, handling all encoding errors"""
    if text is None:
        return ""
    if isinstance(text, bytes):
        return text.decode('utf-8', errors='replace')
    return str(text).encode('utf-8', errors='replace').decode('utf-8')

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    # Ensure proper UTF-8 encoding
                    text += extracted.encode('utf-8', errors='replace').decode('utf-8')
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    text = ""
    try:
        doc = docx.Document(file_path)
        for paragraph in doc.paragraphs:
            para_text = paragraph.text
            # Ensure proper UTF-8 encoding
            para_text = para_text.encode('utf-8', errors='replace').decode('utf-8')
            text += para_text + "\n"
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
        # Check if client is initialized
        if client is None:
            return "Error: GROQ_API_KEY not configured. Please set your API key in the .env file. Get your free API key from https://console.groq.com/keys"
        
        # Safely encode all inputs using the helper function
        cv_text = safe_encode(cv_text)
        target_role = safe_encode(target_role)
        
        # Build the prompt carefully with safe encoding
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
        
        # Ensure response is UTF-8 encoded
        response_text = safe_encode(chat_completion.choices[0].message.content)
        return response_text
    
    except Exception as e:
        # Safely encode error message
        error_msg = safe_encode(str(e))
        return f"Error analyzing CV: {error_msg}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        cv_text = ""
        target_role = request.form.get('target_role', '').strip()
        custom_role = request.form.get('custom_role', '').strip()
        
        # Use custom role if provided, otherwise use dropdown selection
        if custom_role:
            target_role = custom_role
        elif not target_role or target_role == "General Tech Role":
            target_role = "General Professional Role"
        
        # Validate target role
        if len(target_role) > 100:
            return safe_jsonify_error({'error': 'Target role name is too long (max 100 characters).'}, 400)
        
        # Check if file was uploaded
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            
            if file and allowed_file(file.filename):
                # Check file size (max 16MB already set in app config)
                filename = secure_filename(file.filename)
                if not filename:
                    return safe_jsonify_error({'error': 'Invalid filename.'}, 400)
                    
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Extract text from file
                try:
                    cv_text = extract_text_from_file(file_path, filename)
                except Exception as extract_error:
                    # Clean up file even if extraction fails
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return safe_jsonify_error({'error': f'Failed to extract text from file: {safe_encode(str(extract_error))}'}, 400)
                
                # Clean up uploaded file
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to clean up file {file_path}: {cleanup_error}")
            else:
                return safe_jsonify_error({'error': 'Invalid file type. Please upload PDF, DOCX, or TXT files.'}, 400)
        
        # Check if text was pasted
        elif 'cv_text' in request.form and request.form['cv_text'].strip():
            cv_text = request.form['cv_text']
        
        else:
            return safe_jsonify_error({'error': 'Please provide a CV either by uploading a file or pasting text.'}, 400)
        
        # Validate CV text
        if not cv_text or len(cv_text.strip()) < 50:
            return safe_jsonify_error({'error': 'CV text is too short. Please provide a complete CV.'}, 400)
        
        # Analyze with Groq, passing target role
        analysis = analyze_cv_with_groq(cv_text, target_role)
        
        # Store analysis in cache for PDF download
        session_id = str(datetime.now().timestamp())
        analysis_cache[session_id] = {
            'analysis': analysis,
            'target_role': target_role,
            'timestamp': datetime.now()
        }
        
        return safe_jsonify({'analysis': analysis, 'session_id': session_id})
    except Exception as e:
        error_msg = safe_encode(str(e))
        return safe_jsonify_error({'error': f'An error occurred: {error_msg}'}, 500)

@app.route('/health')
def health():
    return safe_jsonify({'status': 'ok', 'message': 'SkillGap AI is running!'})

def generate_pdf_report(analysis_text, target_role):
    """Generate a PDF report from the analysis"""
    # Ensure UTF-8 encoding for PDF generation using safe_encode
    analysis_text = safe_encode(analysis_text)
    target_role = safe_encode(target_role)
    
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
        # Ensure each line is properly UTF-8 encoded using safe_encode
        line = safe_encode(line)
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
        return safe_jsonify_error({'error': 'Report not found. Please analyze a CV first.'}, 404)
    
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
    # Use environment variable for port (Railway sets PORT env var)
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
