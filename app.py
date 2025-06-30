from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import google.generativeai as genai
from dotenv import load_dotenv
import os
import sqlite3
from werkzeug.utils import secure_filename
import tempfile
import fitz  # PyMuPDF for PDFs
from docx import Document  # For Word docs
from datetime import datetime

# Load environment
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database setup
def init_db():
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            response TEXT,
            helpful BOOLEAN,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# File processing
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text(filepath):
    try:
        if filepath.endswith('.pdf'):
            # PDF processing with PyMuPDF
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()
            return text.strip()
        
        elif filepath.endswith('.docx'):
            # Word document processing
            doc = Document(filepath)
            return "\n".join([para.text for para in doc.paragraphs])
        
        elif filepath.endswith('.txt'):
            # Plain text file
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        
        else:
            return "Unsupported file type"
    except Exception as e:
        return f"Error processing file: {str(e)}"

# AI functions
def get_ai_response(prompt, context=None):
    try:
        if context:
            messages = [{"role": "user", "content": msg} for msg in context]
            messages.append({"role": "user", "content": prompt})
            response = model.generate_content(messages)
        else:
            response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# Routes
@app.route('/', methods=['GET', 'POST'])
def home():
    if 'conversation' not in session:
        session['conversation'] = []
    
    # Initialize default values
    response = None
    user_input = None
    
    if request.method == 'POST':
        user_input = request.form.get('user_input', '')
        task_type = request.form.get('task_type', 'answer')
        
        if task_type == 'upload':
            return redirect(url_for('upload_file'))
        
        if user_input:  # Only process if input exists
            response = get_ai_response(user_input, session['conversation'])
            session['conversation'].extend([user_input, response])
            session.modified = True
    
    return render_template('index.html', 
                         response=response or "",
                         user_input=user_input or "",
                         conversation=session['conversation'])

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            extracted_text = extract_text(filepath)
            summary = get_ai_response(f"Summarize this document:\n{extracted_text}")
            
            return render_template('upload.html', 
                                filename=filename,
                                summary=summary,
                                extracted_text=extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text)
    
    return render_template('upload.html')

@app.route('/feedback', methods=['POST'])
def handle_feedback():
    data = request.get_json()
    query = data.get('query')
    response = data.get('response')
    helpful = data.get('helpful', False)
    
    conn = sqlite3.connect('feedback.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO feedback (query, response, helpful)
        VALUES (?, ?, ?)
    ''', (query, response, helpful))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)