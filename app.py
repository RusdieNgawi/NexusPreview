import os
import io
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

load_dotenv()

# Setup Flask
app = Flask(__name__, template_folder='.', static_folder='.')
app.secret_key = os.getenv("SECRET_KEY", "xanadium-super-secret-key-123")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# OAUTH SETUP
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# GEMINI SETUP
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Gunakan 1.5-flash untuk kecepatan dan efisiensi biaya
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    model = None

# --- MIDDLEWARE MAINTENANCE ---
@app.before_request
def check_maintenance():
    # Cek apakah file maintenance.html ada
    if os.path.exists('maintenance.html'):
        # Izinkan akses ke static file atau route maintenance itu sendiri agar tidak infinite loop
        if request.endpoint in ['static', 'maintenance_page']:
            return
        # Render halaman maintenance untuk semua request lain
        return render_template('maintenance.html')

@app.route('/maintenance')
def maintenance_page():
    return render_template('maintenance.html')

# ROUTES UTAMA
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
        return jsonify({'response': 'Akses ditolak atau API Key belum diset.'}), 401
    
    try:
        user_msg = request.form.get('message', '')
        uploaded_file = request.files.get('file')
        
        # Load Persona
        try:
            with open('persona.txt', 'r') as f: persona = f.read()
        except:
            persona = "Anda adalah XanadiumAI, asisten pintar."

        prompt_parts = [persona, "\nUser Query: " + user_msg]

        if uploaded_file:
            filename = uploaded_file.filename.lower()
            mime_type = uploaded_file.mimetype

            # 1. Jika Gambar
            if mime_type.startswith('image/'):
                img = Image.open(io.BytesIO(uploaded_file.read()))
                prompt_parts.append(img)
            
            # 2. Jika File Teks (Python, TXT, HTML, JSON, dll)
            else:
                try:
                    # Baca konten file sebagai teks
                    file_content = uploaded_file.read().decode('utf-8', errors='ignore')
                    prompt_parts.append(f"\n\n[Isi File: {filename}]\n```\n{file_content}\n```")
                    prompt_parts.append("\n(Tolong analisis atau gunakan isi file di atas sesuai instruksi user)")
                except Exception as read_err:
                    return jsonify({'response': f'Gagal membaca file teks: {str(read_err)}'}), 400

        # Generate Response
        response = model.generate_content(prompt_parts)
        return jsonify({'response': response.text})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'response': f'Maaf, terjadi kesalahan server: {str(e)}'}), 500

# Vercel Entrypoint
app = app

if __name__ == '__main__':
    # Untuk Lokal
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(debug=True, port=5000)
