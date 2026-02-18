import os
import io
import json
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

# 1. Load Environment Variables
load_dotenv()

# 2. Setup Flask
app = Flask(__name__, template_folder='.', static_folder='.')

# --- KONFIGURASI KEAMANAN (WAJIB) ---
app.secret_key = os.getenv("SECRET_KEY", "xanadium_kunci_rahasia_default_12345")
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# --- SETUP GOOGLE OAUTH (PERBAIKAN UTAMA) ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    # FIX: Tambahkan URL Metadata secara eksplisit agar tidak error "jwks_uri"
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# --- SETUP GEMINI AI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Error Config Gemini: {e}")
        model = None
else:
    model = None

# --- PERSONA ---
def get_xanadium_persona():
    try:
        with open('persona.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Anda adalah XanadiumAI. Asisten cerdas, futuristik, dan to-the-point."

# ================= ROUTES =================

@app.route('/')
def home():
    """Halaman Utama (Chat)"""
    user_info = session.get('user')
    if not user_info:
        return redirect(url_for('login'))
    
    return render_template('index.html', 
                           user_name=user_info.get('name'),
                           user_email=user_info.get('email'),
                           user_picture=user_info.get('picture'))

@app.route('/login')
def login():
    """Halaman Login"""
    if 'user' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/login/google')
def google_login():
    """Mulai proses login Google"""
    # Secara otomatis mendeteksi apakah HTTP (Lokal) atau HTTPS (Vercel)
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def google_auth():
    """Google mengembalikan user ke sini"""
    try:
        # 1. Ambil Token
        token = google.authorize_access_token()
        
        # 2. Ambil Info User (Cara Paling Aman)
        # Kita coba ambil dari 'userinfo' di dalam token dulu
        user_info = token.get('userinfo')
        
        # Jika kosong, kita paksa fetch manual dari endpoint Google
        if not user_info:
            user_info = google.get('https://www.googleapis.com/oauth2/v3/userinfo').json()
            
        # 3. Simpan ke Session
        session['user'] = user_info
        session.permanent = True
        
        return redirect(url_for('home'))
        
    except Exception as e:
        print(f"LOGIN ERROR: {str(e)}")
        # Tampilkan error di browser agar tahu salahnya dimana
        return f"<h1>Login Gagal</h1><p>Error: {str(e)}</p><a href='/login'>Coba Lagi</a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
def chat():
    """API Chat"""
    if 'user' not in session:
        return jsonify({'response': 'Sesi habis. Silakan login ulang.'}), 401

    if not model:
        return jsonify({'response': 'Error: API Key Server Missing.'}), 500

    try:
        user_msg = request.form.get('message', '')
        img_file = request.files.get('file')
        system_instruction = get_xanadium_persona()
        inputs = []
        
        if img_file:
            image = Image.open(io.BytesIO(img_file.read()))
            prompt = f"{system_instruction}\n\n[USER IMAGE]\nUser: {user_msg}" if user_msg else f"{system_instruction}\n\nAnalisis gambar ini."
            inputs = [prompt, image]
        else:
            if not user_msg: return jsonify({'response': '...'})
            inputs = [f"{system_instruction}\n\nUser: {user_msg}\nXanadium:"]

        response = model.generate_content(inputs)
        return jsonify({'response': response.text})

    except Exception as e:
        return jsonify({'response': f'System Error: {str(e)}'}), 500

# Entry Point Vercel
app = app

if __name__ == '__main__':
    # Konfigurasi agar bisa berjalan di HTTP lokal
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True
