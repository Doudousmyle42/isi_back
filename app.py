from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail, Message
from datetime import datetime
from dotenv import load_dotenv
import database as db
import os
import re
import threading

app = Flask(__name__)

# Configuration CORS
CORS(app, 
     resources={
         r"/api/*": {
             "origins": ["https://isi-front-tau.vercel.app", "http://localhost:3000"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Type"],
             "supports_credentials": False,
             "max_age": 3600
         }
     })

# Configuration Email avec Brevo (fonctionne immédiatement, 300 emails/jour gratuits)
app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('BREVO_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('BREVO_API_KEY')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('BREVO_USERNAME')

mail = Mail(app)

# Initialiser la base de données
try:
    db.init_db()
    print("✅ Base de données initialisée")
except Exception as e:
    print(f"❌ Erreur init DB: {e}")

def validate_email(email):
    """Valide le format d'email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def send_async_email(app, msg):
    """Envoyer un email en arrière-plan"""
    with app.app_context():
        try:
            mail.send(msg)
            print(f"✅ Email envoyé avec succès")
        except Exception as e:
            print(f"❌ Erreur envoi email: {e}")

# Middleware CORS
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ['https://isi-front-tau.vercel.app', 'http://localhost:3000']:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Max-Age', '3600')
    return response

@app.route('/api/send-otp', methods=['POST', 'OPTIONS'])
def send_otp():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400
            
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email requis'}), 400
        
        if not validate_email(email):
            return jsonify({'success': False, 'message': 'Format d\'email invalide'}), 400
        
        # Vérifier si l'email a déjà soumis une idée
        if db.has_submitted(email):
            return jsonify({
                'success': False,
                'message': 'Vous avez déjà soumis une idée avec cet email'
            }), 403
        
        # Générer et sauvegarder l'OTP
        code = db.generate_otp()
        db.save_otp(email, code)
        print(f"✅ OTP généré: {code} pour {email}")
        
        # Préparer et envoyer l'email
        msg = Message(
            subject='Votre code de vérification - Boîte à Idées ISI',
            recipients=[email],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Boîte à Idées ISI</h2>
                <p>Bonjour,</p>
                <p>Votre code de vérification pour soumettre une idée est :</p>
                <div style="background-color: #f3f4f6; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1f2937;">
                        {code}
                    </span>
                </div>
                <p style="color: #6b7280; font-size: 14px;">Ce code expire dans 10 minutes.</p>
                <p style="color: #6b7280; font-size: 14px;">Si vous n'avez pas demandé ce code, ignorez ce message.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="color: #9ca3af; font-size: 12px;">L'équipe ISI</p>
            </div>
            """
        )
        
        # Envoi asynchrone
        thread = threading.Thread(target=send_async_email, args=(app._get_current_object(), msg))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Code envoyé par email'}), 200
        
    except Exception as e:
        print(f"❌ Erreur send_otp: {e}")
        return jsonify({'success': False, 'message': f'Erreur serveur: {str(e)}'}), 500

@app.route('/api/verify-otp', methods=['POST', 'OPTIONS'])
def verify_otp():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400
            
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()
        
        if not email or not code:
            return jsonify({'success': False, 'message': 'Email et code requis'}), 400
        
        if db.verify_otp(email, code):
            print(f"✅ OTP vérifié pour {email}")
            return jsonify({'success': True, 'message': 'Code vérifié'}), 200
        else:
            print(f"❌ OTP invalide pour {email}")
            return jsonify({'success': False, 'message': 'Code invalide ou expiré'}), 401
        
    except Exception as e:
        print(f"❌ Erreur verify_otp: {e}")
        return jsonify({'success': False, 'message': f'Erreur serveur: {str(e)}'}), 500

@app.route('/api/submit-idea', methods=['POST', 'OPTIONS'])
def submit_idea():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400
        
        email = data.get('email', '').strip().lower()
        idea = data.get('idea', '').strip()
        category = data.get('category', '').strip()
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        if not validate_email(email):
            return jsonify({'success': False, 'message': 'Email invalide'}), 400
        
        if len(idea) < 20:
            return jsonify({'success': False, 'message': 'L\'idée doit contenir au moins 20 caractères'}), 400
        
        if not category:
            return jsonify({'success': False, 'message': 'Veuillez sélectionner une catégorie'}), 400
        
        if db.has_submitted(email):
            return jsonify({'success': False, 'message': 'Vous avez déjà soumis une idée avec cet email'}), 403
        
        idea_id = db.save_idea(email, idea, category, timestamp)
        print(f"✅ Idée #{idea_id} soumise par {email}")
        
        return jsonify({
            'success': True,
            'message': 'Idée soumise avec succès',
            'idea_id': idea_id
        }), 201
        
    except Exception as e:
        print(f"❌ Erreur submit_idea: {e}")
        return jsonify({'success': False, 'message': f'Erreur serveur: {str(e)}'}), 500

@app.route('/api/ideas', methods=['GET', 'OPTIONS'])
def get_ideas():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        ideas = db.get_all_ideas()
        return jsonify({'success': True, 'total': len(ideas), 'ideas': ideas}), 200
    except Exception as e:
        print(f"❌ Erreur get_ideas: {e}")
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        stats = db.get_statistics()
        return jsonify({'success': True, 'stats': stats}), 200
    except Exception as e:
        print(f"❌ Erreur get_stats: {e}")
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == 'OPTIONS':
        return '', 200
    
    db_status = "OK"
    try:
        db.get_statistics()
    except Exception as e:
        db_status = f"ERROR: {str(e)}"
    
    return jsonify({
        'status': 'OK',
        'message': 'API Boîte à Idées ISI est en ligne',
        'database': db_status,
        'email_service': 'Brevo',
        'email_configured': bool(app.config.get('MAIL_USERNAME'))
    }), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Bienvenue sur l\'API Boîte à Idées ISI',
        'status': 'online',
        'endpoints': {
            'health': '/api/health (GET)',
            'send_otp': '/api/send-otp (POST)',
            'verify_otp': '/api/verify-otp (POST)',
            'submit_idea': '/api/submit-idea (POST)',
            'get_ideas': '/api/ideas (GET)',
            'get_stats': '/api/stats (GET)'
        }
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Route non trouvée'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Erreur interne'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)