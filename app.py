from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
from groq import Groq
from werkzeug.utils import secure_filename
import PyPDF2
import docx
from dotenv import load_dotenv
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime
import json

# Configure UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    import io
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

os.environ['PYTHONIOENCODING'] = 'utf-8'
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False


# Helper to create safe JSON responses
# Purpose: Convert Python objects to JSON responses with proper UTF-8 encoding
# Functionality:
#   - Recursively processes dictionaries and lists to encode all string values
#   - Uses safe_encode() helper to handle special characters and non-ASCII text
#   - Creates Flask response object with explicit UTF-8 charset header
#   - Sets proper mimetype to ensure browser interprets content as JSON
#   - Handles nested data structures (dicts within lists, etc.)
# Used by: API endpoints that return success responses with data

def safe_jsonify(data):
    """Converts data to JSON response with UTF-8 encoding. Recursively encodes all strings to handle special characters."""
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
        status=200,
        mimetype='application/json; charset=utf-8'
    )
    return response

# Purpose: Convert error data to JSON responses with custom HTTP status codes and UTF-8 encoding
# Functionality:
#   - Similar to safe_jsonify() but accepts custom HTTP status codes (400, 404, 500, etc.)
#   - Recursively encodes all strings in error data to handle special characters
#   - Creates Flask response object with custom status code and UTF-8 charset
#   - Maintains consistent error response format across the application
#   - Prevents encoding errors when returning error messages to clients
# Used by: API endpoints that return error responses with appropriate HTTP status codes

def safe_jsonify_error(data, status_code=500):
    """Converts error data to JSON response with proper HTTP status code and UTF-8 encoding."""
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

# Purpose: Flask middleware that ensures all HTTP response headers have UTF-8 encoding specified
# Functionality:
#   - Runs after every Flask route returns a response (after_request decorator)
#   - Checks if Content-Type header is missing or contains 'application/json'
#   - Appends '; charset=utf-8' to Content-Type headers to explicitly declare UTF-8 encoding
#   - Handles both JSON responses and text/html responses
#   - Prevents browser from misinterpreting special characters in responses
# Used by: Automatically applied to all Flask responses in this application
@app.after_request
def set_utf8_response(response):
    """Ensures all responses have UTF-8 content-type header set correctly."""
    if response.content_type is None or 'application/json' in response.content_type:
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
    elif response.content_type and 'text' in response.content_type:
        response.headers['Content-Type'] = response.content_type.split(';')[0] + '; charset=utf-8'
    return response

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# Initialize Groq AI client
# Purpose: Set up connection to Groq API for CV analysis
# Functionality:
#   - Reads GROQ_API_KEY from .env environment file
#   - Validates API key is not empty and not the default placeholder value
#   - Prints warning message if API key is missing or invalid
#   - Encodes API key to ASCII format to remove any non-ASCII characters
#   - Creates Groq client instance for API communication
#   - Sets client to None if initialization fails (allows graceful degradation)

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY or GROQ_API_KEY == 'your_groq_api_key_here':
    print("WARNING: GROQ_API_KEY not set or using default value!")
    print("Please set your GROQ_API_KEY in the .env file")
    print("Get your API key from: https://console.groq.com/keys")
    client = None
else:
    try:
        GROQ_API_KEY = GROQ_API_KEY.encode('ascii', errors='ignore').decode('ascii')
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"ERROR: Failed to initialize Groq client: {e}")
        client = None

analysis_cache = {}

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

# Purpose: Validate that uploaded files have allowed extensions (security check)
# Functionality:
#   - Checks if filename contains a dot separator
#   - Extracts file extension after the last dot
#   - Converts extension to lowercase for case-insensitive comparison
#   - Verifies extension is in ALLOWED_EXTENSIONS set (txt, pdf, docx)
#   - Returns boolean: True if file type is allowed, False otherwise
# Used by: File upload validation in /analyze route to reject unsupported file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



# Purpose: Safely convert any Python object to a UTF-8 encoded string
# Functionality:
#   - Handles None values by returning empty string
#   - If input is bytes, decodes using UTF-8 (replaces undecodable characters)
#   - Converts any other type to string, encodes to UTF-8, then decodes back
#   - Uses 'replace' error handler to substitute problematic characters with replacement character
#   - Ensures no encoding errors crash the application when handling user data
# Used by: Text processing functions and JSON encoding to prevent encoding errors
def safe_encode(text):
    """Safely converts any text to UTF-8 string, replacing any unencodable characters."""
    if text is None:
        return ""
    if isinstance(text, bytes):
        return text.decode('utf-8', errors='replace')
    return str(text).encode('utf-8', errors='replace').decode('utf-8')

# Purpose: Extract all readable text content from PDF files
# Functionality:
#   - Opens PDF file in binary read mode
#   - Uses PyPDF2 library to read PDF structure
#   - Iterates through every page in the PDF document
#   - Calls extract_text() method on each page to get text content
#   - Encodes extracted text to UTF-8 to handle special characters and international text
#   - Concatenates text from all pages into single string
#   - Returns empty string if file cannot be read or no text found
# Used by: extract_text_from_file() to process .pdf file uploads
def extract_text_from_pdf(file_path):
    """Extracts all text from a PDF file page by page with UTF-8 encoding handling."""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted.encode('utf-8', errors='replace').decode('utf-8')
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

# Purpose: Extract all text content from Microsoft Word (.docx) files
# Functionality:
#   - Opens DOCX file using python-docx library
#   - Iterates through all paragraphs in the document
#   - Extracts text content from each paragraph
#   - Encodes paragraph text to UTF-8 for special character handling
#   - Adds newline character after each paragraph to preserve document structure
#   - Concatenates all paragraphs into single string
#   - Returns empty string if file cannot be read or document is empty
# Used by: extract_text_from_file() to process .docx file uploads
def extract_text_from_docx(file_path):
    """Extracts all paragraph text from a DOCX file with UTF-8 encoding handling."""
    text = ""
    try:
        doc = docx.Document(file_path)
        for paragraph in doc.paragraphs:
            para_text = paragraph.text
            para_text = para_text.encode('utf-8', errors='replace').decode('utf-8')
            text += para_text + "\n"
    except Exception as e:
        print(f"Error reading DOCX: {e}")
    return text

# Purpose: Dispatcher function that extracts text from different file formats
# Functionality:
#   - Extracts file extension from filename (last part after dot)
#   - Converts extension to lowercase for case-insensitive matching
#   - Calls appropriate extraction function based on file type:
#     * .pdf files → extract_text_from_pdf()
#     * .docx files → extract_text_from_docx()
#     * .txt files → reads file directly with UTF-8 encoding
#   - Returns empty string if file type not recognized
# Used by: /analyze route to extract text from user-uploaded CV files
def extract_text_from_file(file_path, filename):
    """Extracts text from file based on its extension (pdf, docx, or txt)."""
    extension = filename.rsplit('.', 1)[1].lower()
    
    if extension == 'pdf':
        return extract_text_from_pdf(file_path)
    elif extension == 'docx':
        return extract_text_from_docx(file_path)
    elif extension == 'txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    return ""

# Purpose: Send CV text to Groq AI API for intelligent skill gap analysis
# Functionality:
#   - Checks if Groq client is initialized (API key is valid)
#   - Encodes all input text (CV and target role) to UTF-8 format
#   - Constructs detailed prompt instructing AI on analysis format and requirements
#   - Specifies prompt structure: missing skills, current skills, learning roadmap, job readiness score, explanation
#   - Sends request to Groq API using llama-3.3-70b-versatile model
#   - Sets temperature to 0.7 for balanced creativity and consistency
#   - Receives AI-generated analysis response
#   - Encodes response to UTF-8 to handle special characters in output
#   - Returns formatted analysis string or error message
# Used by: /analyze route to generate skill gap analysis reports
def analyze_cv_with_groq(cv_text, target_role="General Professional Role"):
    """Analyzes CV text using Groq AI to identify skill gaps, create learning roadmap, and provide job readiness score."""
    try:
        if client is None:
            return "Error: GROQ_API_KEY not configured. Please set your API key in the .env file. Get your free API key from https://console.groq.com/keys"
        
        cv_text = safe_encode(cv_text)
        target_role = safe_encode(target_role)
        
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
        
        response_text = safe_encode(chat_completion.choices[0].message.content)
        return response_text
    
    except Exception as e:
        error_msg = safe_encode(str(e))
        return f"Error analyzing CV: {error_msg}"

# Purpose: Serve the main landing page HTML template
# Functionality:
#   - Flask route handler for GET requests to '/' (root URL)
#   - Renders and returns index.html template from templates folder
#   - Displays main application interface with CV upload form
#   - Contains problem/solution overview and usage instructions
# Used by: Browsers accessing the application's main URL
@app.route('/')
def index():
    return render_template('index.html')

# Purpose: Process CV file uploads or text input and generate skill gap analysis
# Functionality:
#   - Flask route handler for POST requests to '/analyze'
#   - Extracts target role from form (dropdown or custom text input)
#   - Validates target role name length (max 100 characters)
#   - Handles file upload: validates file type, extracts text content
#   - Alternative: accepts pasted CV text directly from form
#   - Validates CV text has minimum length (50 characters)
#   - Calls analyze_cv_with_groq() to get AI-powered analysis
#   - Stores analysis in cache with session ID for PDF download later
#   - Returns JSON response with analysis text and session ID
#   - Returns error responses for invalid inputs or processing failures
# Used by: Frontend form submission when user clicks "Analyze My Skills"

@app.route('/analyze', methods=['POST'])
def analyze():
    """Processes CV upload/text input and returns AI-powered skill gap analysis with job readiness score."""
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

# Purpose: Provide health check endpoint for monitoring application status
# Functionality:
#   - Flask route handler for GET requests to '/health'
#   - Returns simple JSON response with status 'ok' and status message
#   - Used by deployment platforms (Railway, Render) to verify app is running
#   - Helps detect if application has crashed or become unresponsive
# Used by: Monitoring services and deployment platforms
@app.route('/health')
def health():
    return safe_jsonify({'status': 'ok', 'message': 'SkillGap AI is running!'})

# Purpose: Generate a formatted, professional PDF document from skill gap analysis results
# Functionality:
#   - Encodes all text input (analysis and target role) to UTF-8 format
#   - Creates BytesIO buffer to hold PDF data in memory
#   - Initializes ReportLab PDF document with letter size page and margins
#   - Defines custom paragraph styles for title, headings, normal text, steps, and scores
#   - Adds PDF elements: title, target role, generation timestamp, horizontal divider
#   - Parses analysis text line-by-line and formats appropriately:
#     * Markdown-style headings (**text**) become section headers
#     * Bullet points (-) become formatted bullet lists
#     * Lines starting with 'Step' become highlighted roadmap items
#     * Score lines become bold and colored
#   - Adds footer with application branding
#   - Builds final PDF document and returns buffer positioned at start
# Used by: /download-pdf route to create downloadable PDF reports
def generate_pdf_report(analysis_text, target_role):
    """Generates a formatted PDF report from skill gap analysis with styling and layout."""
    analysis_text = safe_encode(analysis_text)
    target_role = safe_encode(target_role)
    
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                          rightMargin=0.5*inch, leftMargin=0.5*inch,
                          topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=10,
        alignment=1
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
    
    elements.append(Paragraph("SkillGap AI - Skill Gap Analysis Report", title_style))
    elements.append(Paragraph(f"Target Role: <b>{target_role}</b>", heading_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", normal_style))
    elements.append(Spacer(1, 0.3*inch))
    
    divider_data = [['']]
    divider_table = Table(divider_data, colWidths=[7.5*inch])
    divider_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 2, colors.HexColor('#667eea')),
    ]))
    elements.append(divider_table)
    elements.append(Spacer(1, 0.2*inch))
    
    lines = analysis_text.split('\n')
    
    for line in lines:
        line = safe_encode(line)
        if line.strip() == '':
            elements.append(Spacer(1, 0.05*inch))
        elif line.strip().startswith('**') and line.strip().endswith('**'):
            heading_text = line.strip().replace('**', '')
            elements.append(Paragraph(heading_text, heading_style))
        elif line.strip().startswith('-') or line.strip().startswith('•'):
            bullet_text = line.strip().lstrip('-•').strip()
            elements.append(Paragraph(f"• {bullet_text}", normal_style))
        elif line.strip().startswith('Step'):
            elements.append(Paragraph(line.strip(), ParagraphStyle(
                'StepStyle',
                parent=normal_style,
                leftIndent=0.2*inch,
                backgroundColor=colors.HexColor('#f3f0ff'),
                borderPadding=5
            )))
        elif line.strip().startswith('Score:'):
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
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Purpose: Retrieve cached analysis and return it as downloadable PDF file
# Functionality:
#   - Flask route handler for GET requests to '/download-pdf/<session_id>'
#   - Looks up session_id in analysis_cache dictionary
#   - Returns 404 error if session not found in cache
#   - Retrieves cached analysis text and target role from session data
#   - Calls generate_pdf_report() to create formatted PDF document
#   - Generates descriptive filename including target role and timestamp
#   - Returns PDF file with:
#     * Proper MIME type (application/pdf)
#     * as_attachment=True flag to trigger download in browser
#     * download_name parameter for filename
# Used by: Frontend "Download PDF" button to deliver analysis reports to users
@app.route('/download-pdf/<session_id>')
def download_pdf(session_id):
    """Retrieves cached analysis and returns it as a downloadable PDF file."""
    if session_id not in analysis_cache:
        return safe_jsonify_error({'error': 'Report not found. Please analyze a CV first.'}, 404)
    
    cached_data = analysis_cache[session_id]
    analysis_text = cached_data['analysis']
    target_role = cached_data['target_role']
    
    pdf_buffer = generate_pdf_report(analysis_text, target_role)
    
    filename = f"SkillGap_Analysis_{target_role.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

# Application entry point
# Purpose: Start the Flask development/production server
# Functionality:
#   - Reads PORT environment variable (set by Railway/deployment platforms, defaults to 5000)
#   - Reads FLASK_ENV to determine debug mode (development=True, production=False)
#   - Starts Flask application server listening on all interfaces (0.0.0.0)
#   - Makes app accessible from any network address, not just localhost
if __name__ == '__main__':
    # Use environment variable for port (Railway sets PORT env var)
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
