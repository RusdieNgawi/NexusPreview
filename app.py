import os
import io
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# 1. Load Env
load_dotenv()

# Konfigurasi Flask (Tanpa folder templates, index.html di root)
app = Flask(__name__, template_folder='.', static_folder='.')

# 2. Setup API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        print(f"Error Config: {e}")
        model = None
else:
    model = None

# --- FUNGSI MEMUAT PERSONA ---
def get_nexus_persona():
    """Membaca instruksi gaya dari file persona.txt"""
    try:
        # Coba baca file eksternal
        with open('persona.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback jika file tidak ada
        return (
            "Anda adalah Nexus AI. Asisten futuristik. "
            "Jawab singkat, padat, dan jelas dalam Bahasa Indonesia."
        )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    if not model:
        return jsonify({'response': 'Error: API Key bermasalah.'}), 500

    try:
        user_msg = request.form.get('message', '')
        img_file = request.files.get('file')
        
        # 3. AMBIL GAYA DARI FILE
        system_instruction = get_nexus_persona()
        
        inputs = []
        
        if img_file:
            # Proses Gambar
            image_bytes = img_file.read()
            image = Image.open(io.BytesIO(image_bytes))
            
            prompt = f"{system_instruction}\n\n[USER IMAGE CONTEXT]\n"
            if user_msg:
                prompt += f"User bertanya: {user_msg}"
            else:
                prompt += "Jelaskan gambar ini sesuai kepribadianmu."
                
            inputs = [prompt, image]
        else:
            # Proses Teks
            if not user_msg: return jsonify({'response': '...'})
            
            full_prompt = f"{system_instruction}\n\nUser: {user_msg}\nNexus:"
            inputs = [full_prompt]

        response = model.generate_content(inputs)
        return jsonify({'response': response.text})

    except Exception as e:
        return jsonify({'response': f'Maaf, sistem error: {str(e)}'}), 500

# Vercel entry point
app = app

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port, debug=True)

