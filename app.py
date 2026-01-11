from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail, Message
from datetime import datetime
from dotenv import load_dotenv
import database as db
import os
import re

app = Flask(__name__)

# Configuration CORS
CORS(app, 
     origins="*",
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=False)


# Configuration Email depuis variables d'environnement
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# Initialiser la base de données
db.init_db()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def validate_email(email):
    """Valide le format d'email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return '', 204

@app.route('/api/send-otp', methods=['POST', 'OPTIONS'])
def send_otp():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Format d\'email invalide'
            }), 400
        
        # Vérifier si l'email a déjà soumis une idée
        if db.has_submitted(email):
            return jsonify({
                'success': False,
                'message': 'Vous avez déjà soumis une idée avec cet email'
            }), 403
        
        # Générer et sauvegarder l'OTP
        code = db.generate_otp()
        db.save_otp(email, code)
        
        # Envoyer l'email
        try:
            msg = Message(
                subject='Votre code de vérification - Boîte à Idées ISI',
                recipients=[email],
                body=f'''Bonjour,

Votre code de vérification pour soumettre une idée est :

{code}

Ce code expire dans 10 minutes.

Si vous n'avez pas demandé ce code, ignorez ce message.

Cordialement,
L'équipe ISI
'''
            )
            mail.send(msg)
            
            return jsonify({
                'success': True,
                'message': 'Code envoyé par email'
            }), 200
        except Exception as e:
            print(f"Erreur envoi email: {e}")
            return jsonify({
                'success': False,
                'message': 'Erreur lors de l\'envoi de l\'email'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur serveur: {str(e)}'
        }), 500

@app.route('/api/verify-otp', methods=['POST', 'OPTIONS'])
def verify_otp():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()
        
        if not email or not code:
            return jsonify({
                'success': False,
                'message': 'Email et code requis'
            }), 400
        
        # Vérifier l'OTP
        if db.verify_otp(email, code):
            return jsonify({
                'success': True,
                'message': 'Code vérifié'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Code invalide ou expiré'
            }), 401
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur serveur: {str(e)}'
        }), 500

@app.route('/api/submit-idea', methods=['POST', 'OPTIONS'])
def submit_idea():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        
        email = data.get('email', '').strip().lower()
        idea = data.get('idea', '').strip()
        category = data.get('category', '').strip()
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        # Validations
        if not validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Email invalide'
            }), 400
        
        if len(idea) < 20:
            return jsonify({
                'success': False,
                'message': 'L\'idée doit contenir au moins 20 caractères'
            }), 400
        
        if not category:
            return jsonify({
                'success': False,
                'message': 'Veuillez sélectionner une catégorie'
            }), 400
        
        # Vérifier si l'étudiant a déjà soumis une idée
        if db.has_submitted(email):
            return jsonify({
                'success': False,
                'message': 'Vous avez déjà soumis une idée avec cet email'
            }), 403
        
        # Enregistrer l'idée
        idea_id = db.save_idea(email, idea, category, timestamp)
        
        return jsonify({
            'success': True,
            'message': 'Idée soumise avec succès',
            'idea_id': idea_id
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur serveur: {str(e)}'
        }), 500

@app.route('/api/ideas', methods=['GET', 'OPTIONS'])
def get_ideas():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        ideas = db.get_all_ideas()
        return jsonify({
            'success': True,
            'total': len(ideas),
            'ideas': ideas
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        stats = db.get_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == 'OPTIONS':
        return '', 204
        
    return jsonify({
        'status': 'OK',
        'message': 'API Boîte à Idées ISI est en ligne'
    }), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Bienvenue sur l\'API Boîte à Idées ISI',
        'status': 'online',
        'endpoints': {
            'health': '/api/health',
            'send_otp': '/api/send-otp (POST)',
            'verify_otp': '/api/verify-otp (POST)',
            'submit_idea': '/api/submit-idea (POST)',
            'get_ideas': '/api/ideas (GET)',
            'get_stats': '/api/stats (GET)'
        }
    }), 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)