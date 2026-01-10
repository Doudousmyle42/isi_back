from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import database as db
import re

app = Flask(__name__)

# Configuration CORS complète et permissive
CORS(app, 
     origins="*",
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=False)

# Middleware CORS manuel pour gérer les preflight requests
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Initialiser la base de données
db.init_db()

def validate_email(email):
    """Valide que l'email est au format @groupeisi.com"""
    pattern = r'^[a-zA-Z0-9._%+-]+@groupeisi\.com$'
    return re.match(pattern, email) is not None

# Route OPTIONS pour toutes les routes API (preflight)
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return '', 204

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
                'message': 'Email invalide. Utilisez votre email @groupeisi.com'
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
        
    """Récupérer toutes les idées (pour l'administration)"""
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

@app.route('/api/ideas/category/<category>', methods=['GET', 'OPTIONS'])
def get_ideas_by_category(category):
    if request.method == 'OPTIONS':
        return '', 204
        
    """Récupérer les idées par catégorie"""
    try:
        ideas = db.get_ideas_by_category(category)
        return jsonify({
            'success': True,
            'category': category,
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
        
    """Obtenir des statistiques"""
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
        
    """Vérifier que l'API fonctionne"""
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
            'submit_idea': '/api/submit-idea (POST)',
            'get_ideas': '/api/ideas (GET)',
            'get_stats': '/api/stats (GET)'
        }
    }), 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)