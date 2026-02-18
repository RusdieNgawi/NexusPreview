import os
import io
import json
# Tambahkan 'datetime' untuk mengatur durasi login
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

# 1. Load Environment Variables
load_dotenv()

# 2. Setup Flask (Template & Static di Root)
app = Flask(__name__, template_folder='.', static_folder='.')

# --- KONFIGURASI KEAMANAN SESI (CRITICAL) ---
# Tanpa secret_key, login TIDAK AKAN BERFUNGSI.
# Saya berikan nilai default agar tidak error jika .env kosong.
app.secret_key = os.getenv("SECRET_KEY", "xanadium_dev_secret_key_999")

# Konfigurasi agar Cookie Login awet & aman di Localhost
app.config['SESSION_COOKIE_NAME'] = 'xanadium-session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7) # Login tahan 7 hari
app.config['SESSION_COOKIE_SECURE'] = False # False untuk Localhost (HTTP), True nanti untuk Vercel (HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = True

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

# --- FUNGSI BANTUAN ---
def get_xanadium_persona():
    try:
        with open('persona.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Anda adalah XanadiumAI. Asisten cerdas, futuristik, dan to-the-point."

# ================= ROUTES =================

@app.route('/')
def home():
    """Halaman Utama (Chat) - Diproteksi"""
    # Cek apakah user ada di sesi
    user_info = session.get('user')
    
    if not user_info:
        # Jika belum login, tendang ke halaman login
        return redirect(url_for('login'))
    
    # Jika sudah login, tampilkan chat
    return render_template('index.html', 
                           user_name=user_info.get('name'),
                           user_email=user_info.get('email'),
                           user_picture=user_info.get('picture'))

@app.route('/login')
def login():
    """Halaman Login"""
    # Jika user iseng buka /login padahal sudah login, balikkan ke home
    if 'user' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/login/google')
def google_login():
    """Mulai proses login Google"""
    redirect_uri = url_for('google_auth', _external=True)
    # Print untuk debugging URL callback
    print(f"DEBUG: Redirecting to Google with callback: {redirect_uri}")
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def google_auth():
    """Google mengembalikan user ke sini"""
    try:
        # 1. Tukar kode dengan token akses
        token = google.authorize_access_token()
        
        # 2. Ambil data profil user dari Google
        user_info = google.get('userinfo').json()
        
        if not user_info:
            return "Gagal mengambil data user dari Google (User Info Empty)", 400

        # 3. SIMPAN KE SESSION (PENTING)
        session.permanent = True  # Agar login awet (sesuai config 7 hari)
        session['user'] = user_info
        
        print(f"DEBUG: Login Berhasil untuk {user_info.get('email')}")
        
        # 4. Redirect ke Home
        return redirect(url_for('home'))
        
    except Exception as e:
        print(f"ERROR LOGIN: {e}")
        return f"Login Gagal: {str(e)} <br> <a href='/login'>Coba Lagi</a>"

@app.route('/logout')
def logout():
    """Hapus sesi"""
    session.clear() # Hapus semua data sesi
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
        return jsonify({'response': f'Error System: {str(e)}'}), 500

# Entry Point Vercel
app = app

if __name__ == '__main__':
    # IZINKAN HTTP (PENTING UNTUK LOCALHOST)
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    # Gunakan port 5000 default
    port = int(os.environ.get("PORT", 5000))
    print(f"Mulai server Xanadium di http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)

