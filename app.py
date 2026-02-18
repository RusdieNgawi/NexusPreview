import os
import io
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

load_dotenv()

# Gunakan template_folder='.' karena index.html kamu ada di root
app = Flask(__name__, template_folder='.', static_folder='.')
app.secret_key = os.getenv("SECRET_KEY", "xanadium-super-secret-key-123")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# KONFIGURASI OAUTH MANUAL (Mencegah Missing jwks_uri)
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# API Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    model = None

# --- ROUTES ---

@app.route('/')
def home():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    return render_template('index.html', 
                           user_name=user.get('name'), 
                           user_picture=user.get('picture'),
                           user_email=user.get('email'))

@app.route('/login')
def login():
    if 'user' in session: return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def google_auth():
    try:
        token = google.authorize_access_token()
        # Ambil userinfo langsung dari token (lebih cepat & stabil di Vercel)
        user_info = token.get('userinfo')
        if not user_info:
            user_info = google.get('https://openidconnect.googleapis.com/v1/userinfo').json()
            
        session['user'] = user_info
        session.permanent = True
        return redirect(url_for('home'))
    except Exception as e:
        return f"Login Gagal: {str(e)} <br> <a href='/login'>Coba Lagi</a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
def chat():
    if 'user' not in session or not model:
        return jsonify({'response': 'Akses ditolak atau sistem belum siap.'}), 401
    try:
        user_msg = request.form.get('message', '')
        img_file = request.files.get('file')
        
        # Baca Persona
        try:
            with open('persona.txt', 'r') as f: persona = f.read()
        except:
            persona = "Anda adalah XanadiumAI."

        if img_file:
            image = Image.open(io.BytesIO(img_file.read()))
            response = model.generate_content([f"{persona}\n\n{user_msg}", image])
        else:
            response = model.generate_content(f"{persona}\n\nUser: {user_msg}")
            
        return jsonify({'response': response.text})
    except Exception as e:
        return jsonify({'response': f'Error: {str(e)}'}), 500

# Vercel Entrypoint
app = app
