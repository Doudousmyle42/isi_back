from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import database as db
import re

app = Flask(__name__)
CORS(app)  # Permet les requêtes depuis Vercel

# Initialiser la base de données
db.init_db()

def validate_email(email):
    """Valide que l'email est au format @isi.com"""
    pattern = r'^[a-zA-Z0-9._%+-]+@isi\.com$'
    return re.match(pattern, email) is not None

@app.route('/api/submit-idea', methods=['POST'])
def submit_idea():
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
                'message': 'Email invalide. Utilisez votre email @isi.com'
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

@app.route('/api/ideas', methods=['GET'])
def get_ideas():
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

@app.route('/api/ideas/category/<category>', methods=['GET'])
def get_ideas_by_category(category):
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

@app.route('/api/stats', methods=['GET'])
def get_stats():
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

@app.route('/api/health', methods=['GET'])
def health_check():
    """Vérifier que l'API fonctionne"""
    return jsonify({
        'status': 'OK',
        'message': 'API Boîte à Idées ISI est en ligne'
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)