import os
import io
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Setup Flask
app = Flask(__name__, template_folder='.', static_folder='.')

# API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Error Config: {e}")
        model = None
else:
    model = None

# System Prompt
def get_xanadium_persona():
    try:
        with open('persona.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return (
            "Anda adalah XanadiumAI. "
            "Identitas: Sistem AI modern dan minimalis. "
            "Gaya Bicara: Profesional, langsung pada inti (to-the-point), dan canggih. "
            "Jangan pernah mengaku sebagai Gemini atau Google. "
            "Jawab dalam Bahasa Indonesia dengan format Markdown."
        )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    if not model:
        return jsonify({'response': 'System Error: API Key server missing.'}), 500

    try:
        user_msg = request.form.get('message', '')
        img_file = request.files.get('file')
        
        system_instruction = get_xanadium_persona()
        inputs = []
        
        if img_file:
            image_bytes = img_file.read()
            image = Image.open(io.BytesIO(image_bytes))
            prompt = f"{system_instruction}\n\n[USER IMAGE]\nUser bertanya: {user_msg}" if user_msg else f"{system_instruction}\n\nAnalisis gambar ini."
            inputs = [prompt, image]
        else:
            if not user_msg: return jsonify({'response': 'Menunggu data...'})
            full_prompt = f"{system_instruction}\n\nUser: {user_msg}\nXanadium:"
            inputs = [full_prompt]

        response = model.generate_content(inputs)
        return jsonify({'response': response.text})

    except Exception as e:
        return jsonify({'response': f'Terjadi kesalahan: {str(e)}'}), 500

# Vercel Entry Point
app = app

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port, debug=True)
