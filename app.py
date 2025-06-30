from flask import Flask, render_template, request, session, jsonify
import google.generativeai as genai
from dotenv import load_dotenv
import os
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from docx import Document
import re
from database import init_db, log_conversation, log_feedback
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize
load_dotenv()
init_db()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Constants
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text(filepath):
    try:
        if filepath.endswith('.pdf'):
            doc = fitz.open(filepath)
            return " ".join(page.get_text() for page in doc)
        elif filepath.endswith('.docx'):
            return "\n".join(p.text for p in Document(filepath).paragraphs)
        elif filepath.endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        return "Unsupported file type"
    except Exception as e:
        return f"Error processing file: {str(e)}"

def format_response(text):
    # Markdown to HTML conversion
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'\$(.*?)\$', r'<div class="math-equation">\1</div>', text)
    text = re.sub(r'```(.*?)```', r'<pre class="code-block">\1</pre>', text, flags=re.DOTALL)
    text = re.sub(r'^- (.*)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = text.replace('\n<li>', '<ul><li>').replace('</li>\n', '</li></ul>')
    text = re.sub(r'(\d+)\. (.*)', r'<li>\2</li>', text)
    text = re.sub(r'(<li>.*<\/li>)', r'<ol>\1</ol>', text)
    return text.replace('\n', '<br>')

@app.route('/')
def index():
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
@limiter.limit("10 per minute")
def handle_chat():
    if 'session_id' not in session:
        return jsonify({'error': 'Session expired'}), 401

    user_input = request.json.get('message', '').strip()
    if not user_input:
        return jsonify({'error': 'Empty message'}), 400

    try:
        response = model.generate_content(user_input).text
        formatted_response = format_response(response)
        
        log_conversation(
            session['session_id'],
            user_input,
            response
        )
        
        return jsonify({
            'response': formatted_response,
            'raw_response': response
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
@limiter.limit("5 per minute")
def handle_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type'}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        text = extract_text(filepath)
        if text.startswith("Error:"):
            return jsonify({'error': text}), 500

        prompt = f"""
        Analyze this document and provide:
        1. Comprehensive summary
        2. Key findings/data points
        3. Actionable insights
        
        Document content:
        {text[:15000]}
        """
        
        response = model.generate_content(prompt).text
        os.remove(filepath)
        
        return jsonify({
            'filename': filename,
            'summary': format_response(response),
            'preview': text[:500] + ('...' if len(text) > 500 else '')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def handle_feedback():
    data = request.json
    if not data or 'query' not in data or 'response' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    try:
        log_feedback(
            data['query'],
            data['response'],
            data.get('helpful', False)
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)