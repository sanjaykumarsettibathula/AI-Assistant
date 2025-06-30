from flask import Flask, render_template, request, session, jsonify
import google.generativeai as genai
from dotenv import load_dotenv
import os
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from docx import Document
import re
from database import init_db, log_conversation, log_feedback

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

# Constants
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        return f"Error: {str(e)}"

def format_response(text):
    # Markdown to HTML conversion
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'\$(.*?)\$', r'<div class="math">\1</div>', text)
    text = re.sub(r'```(.*?)```', r'<pre class="code">\1</pre>', text, flags=re.DOTALL)
    text = re.sub(r'^-\s(.*)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = text.replace('\n\n', '<br>')
    return text

@app.route('/')
def home():
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    user_input = request.json.get('message', '').strip()
    if not user_input:
        return jsonify({'error': 'Empty message'}), 400
    
    try:
        response = model.generate_content(user_input).text
        formatted = format_response(response)
        log_conversation(session['session_id'], user_input, response)
        return jsonify({'response': formatted})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def handle_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
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
        
        prompt = f"Analyze this document and provide:\n1. Key points\n2. Important data\n3. Actionable insights\n\n{text[:15000]}"
        response = model.generate_content(prompt).text
        os.remove(filepath)
        
        return jsonify({
            'response': format_response(response),
            'preview': text[:500] + ('...' if len(text) > 500 else '')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def handle_feedback():
    data = request.json
    log_feedback(
        session['session_id'],
        data.get('query', ''),
        data.get('response', ''),
        data.get('helpful', False)
    )
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)