from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail, Message
from datetime import datetime
from dotenv import load_dotenv
import database as db
import os
import re
import threading
import traceback

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

# Configuration Email
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_SUPPRESS_SEND'] = False
app.config['MAIL_TIMEOUT'] = 30

# Vérifier la config email au démarrage
if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
    print("⚠️ ATTENTION: Configuration email manquante!")
    print(f"MAIL_USERNAME: {'Configuré' if app.config['MAIL_USERNAME'] else 'MANQUANT'}")
    print(f"MAIL_PASSWORD: {'Configuré' if app.config['MAIL_PASSWORD'] else 'MANQUANT'}")

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

def send_async_email(app, msg, email):
    """Envoyer un email en arrière-plan"""
    with app.app_context():
        try:
            mail.send(msg)
            print(f"✅ Email envoyé avec succès à {email}")
        except Exception as e:
            print(f"❌ Erreur envoi email async à {email}: {e}")
            print(traceback.format_exc())

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
        # Vérifier la configuration email
        if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
            print("❌ Configuration email manquante")
            return jsonify({
                'success': False,
                'message': 'Service email non configuré. Contactez l\'administrateur.'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Données manquantes'
            }), 400
            
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({
                'success': False,
                'message': 'Email requis'
            }), 400
        
        if not validate_email(email):
            return jsonify({
                'success': False,
                'message': 'Format d\'email invalide'
            }), 400
        
        # Vérifier si l'email a déjà soumis une idée
        try:
            if db.has_submitted(email):
                return jsonify({
                    'success': False,
                    'message': 'Vous avez déjà soumis une idée avec cet email'
                }), 403
        except Exception as e:
            print(f"❌ Erreur has_submitted: {e}")
            return jsonify({
                'success': False,
                'message': 'Erreur de vérification'
            }), 500
        
        # Générer et sauvegarder l'OTP
        try:
            code = db.generate_otp()
            db.save_otp(email, code)
            print(f"✅ OTP généré: {code} pour {email}")
        except Exception as e:
            print(f"❌ Erreur génération OTP: {e}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': 'Erreur lors de la génération du code'
            }), 500
        
        # Préparer l'email
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
            
            # Envoyer l'email de manière asynchrone
            thread = threading.Thread(
                target=send_async_email, 
                args=(app._get_current_object(), msg, email)
            )
            thread.daemon = True
            thread.start()
            
            print(f"✅ Thread email démarré pour {email}")
            
        except Exception as e:
            print(f"❌ Erreur préparation email: {e}")
            print(traceback.format_exc())
            # On retourne quand même success car l'OTP est sauvegardé
            return jsonify({
                'success': True,
                'message': 'Code généré (email en cours d\'envoi)',
                'warning': 'L\'envoi de l\'email peut prendre quelques instants'
            }), 200
        
        # Répondre immédiatement
        return jsonify({
            'success': True,
            'message': 'Code envoyé par email'
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur send_otp: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Erreur serveur: {str(e)}'
        }), 500

@app.route('/api/verify-otp', methods=['POST', 'OPTIONS'])
def verify_otp():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Données manquantes'
            }), 400
            
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()
        
        if not email or not code:
            return jsonify({
                'success': False,
                'message': 'Email et code requis'
            }), 400
        
        # Vérifier l'OTP
        if db.verify_otp(email, code):
            print(f"✅ OTP vérifié pour {email}")
            return jsonify({
                'success': True,
                'message': 'Code vérifié'
            }), 200
        else:
            print(f"❌ OTP invalide pour {email}")
            return jsonify({
                'success': False,
                'message': 'Code invalide ou expiré'
            }), 401
        
    except Exception as e:
        print(f"❌ Erreur verify_otp: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Erreur serveur: {str(e)}'
        }), 500

@app.route('/api/submit-idea', methods=['POST', 'OPTIONS'])
def submit_idea():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Données manquantes'
            }), 400
        
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
        
        print(f"✅ Idée #{idea_id} soumise par {email}")
        
        return jsonify({
            'success': True,
            'message': 'Idée soumise avec succès',
            'idea_id': idea_id
        }), 201
        
    except Exception as e:
        print(f"❌ Erreur submit_idea: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Erreur serveur: {str(e)}'
        }), 500

@app.route('/api/ideas', methods=['GET', 'OPTIONS'])
def get_ideas():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        ideas = db.get_all_ideas()
        return jsonify({
            'success': True,
            'total': len(ideas),
            'ideas': ideas
        }), 200
    except Exception as e:
        print(f"❌ Erreur get_ideas: {e}")
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        stats = db.get_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        print(f"❌ Erreur get_stats: {e}")
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == 'OPTIONS':
        return '', 200
    
    # Test de la connexion DB
    db_status = "OK"
    try:
        db.get_statistics()
    except Exception as e:
        db_status = f"ERROR: {str(e)}"
    
    # Test de la config email
    email_config = {
        'server': app.config.get('MAIL_SERVER'),
        'port': app.config.get('MAIL_PORT'),
        'username_set': bool(app.config.get('MAIL_USERNAME')),
        'password_set': bool(app.config.get('MAIL_PASSWORD'))
    }
        
    return jsonify({
        'status': 'OK',
        'message': 'API Boîte à Idées ISI est en ligne',
        'cors': 'enabled',
        'database': db_status,
        'email': email_config
    }), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Bienvenue sur l\'API Boîte à Idées ISI',
        'status': 'online',
        'cors': 'enabled',
        'endpoints': {
            'health': '/api/health (GET)',
            'send_otp': '/api/send-otp (POST)',
            'verify_otp': '/api/verify-otp (POST)',
            'submit_idea': '/api/submit-idea (POST)',
            'get_ideas': '/api/ideas (GET)',
            'get_stats': '/api/stats (GET)'
        }
    }), 200

# Gestion des erreurs
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Route non trouvée'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"❌ Erreur 500: {error}")
    print(traceback.format_exc())
    return jsonify({
        'success': False,
        'message': 'Erreur interne du serveur'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)