import os
import io
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

# 1. Load Environment Variables
load_dotenv()

# 2. Setup Flask (Root Directory)
app = Flask(__name__, template_folder='.', static_folder='.')

# --- KONFIGURASI KEAMANAN (WAJIB) ---
# Secret Key digunakan untuk mengunci sesi login. 
# Jika ini berubah, semua user akan ter-logout otomatis.
app.secret_key = os.getenv("SECRET_KEY", "xanadium_super_secret_key_random_123")
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'

# --- SETUP GOOGLE OAUTH ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    # Scope penting: openid, email, dan profile (untuk foto user)
    client_kwargs={'scope': 'openid email profile'},
)

# --- SETUP GEMINI AI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Gemini Config Error: {e}")
        model = None
else:
    model = None

# --- PERSONA XANADIUM ---
def get_xanadium_persona():
    try:
        with open('persona.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Anda adalah XanadiumAI. Asisten cerdas, futuristik, dan to-the-point."

# ================= ROUTES (JALUR AKSES) =================

@app.route('/')
def home():
    """
    Halaman Utama (Chat).
    DIPROTEKSI: Hanya bisa diakses jika user sudah login.
    """
    user_info = session.get('user')
    
    # LOGIKA SATPAM:
    if not user_info:
        # Jika tidak ada info user di session, lempar ke halaman login
        return redirect(url_for('login'))
    
    # Jika ada, tampilkan index.html dengan data user
    return render_template('index.html', 
                           user_name=user_info.get('name'),
                           user_email=user_info.get('email'),
                           user_picture=user_info.get('picture'))

@app.route('/login')
def login():
    """Halaman Login (Pintu Gerbang)"""
    # Jika user iseng buka /login padahal sudah login, kembalikan ke home
    if 'user' in session:
        return redirect(url_for('home'))
        
    return render_template('login.html')

@app.route('/login/google')
def google_login():
    """Tombol 'Lanjutkan dengan Google' mengarah ke sini"""
    # Buat URL callback otomatis berdasarkan host (localhost atau vercel)
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def google_auth():
    """Google mengirim user kembali ke sini setelah sukses login"""
    try:
        token = google.authorize_access_token()
        user_info = google.get('userinfo').json()
        
        # SIMPAN DATA USER KE SESSION (Browser mengingat login ini)
        session['user'] = user_info
        
        # Login sukses, masuk ke Home
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Login Failed: {e}")
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Hapus sesi dan tendang ke halaman login"""
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
def chat():
    """API Chat (DIPROTEKSI)"""
    # Cek login dulu sebelum boleh chat
    if 'user' not in session:
        return jsonify({'response': 'Sesi Anda telah berakhir. Silakan refresh halaman.'}), 401

    if not model:
        return jsonify({'response': 'Error: Server API Key missing.'}), 500

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

# Vercel Entry Point
app = app

if __name__ == '__main__':
    # IZINKAN HTTP UNTUK LOKAL (PENTING AGAR TIDAK ERROR DI LOCALHOST)
    # Saat di Vercel (Production), ini tidak akan berpengaruh karena pakai HTTPS
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

