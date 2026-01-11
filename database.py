import psycopg
from psycopg.rows import dict_row
import os
from datetime import datetime, timedelta
import json
import secrets

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """Créer une connexion à la base de données PostgreSQL"""
    try:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        return conn
    except Exception as e:
        print(f"❌ Erreur de connexion à la base de données: {e}")
        raise

def init_db():
    """Initialiser la base de données PostgreSQL"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Table des idées
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ideas (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                idea TEXT NOT NULL,
                category VARCHAR(100) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table des OTP
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS otp_codes (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                code VARCHAR(6) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Index pour nettoyer les vieux OTP
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_otp_expires 
            ON otp_codes(expires_at)
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Base de données PostgreSQL initialisée")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base de données: {e}")
        raise

def generate_otp():
    """Générer un code OTP à 6 chiffres"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

def save_otp(email, code):
    """Enregistrer un code OTP"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Expiration dans 10 minutes
        expires_at = datetime.now() + timedelta(minutes=10)
        
        cursor.execute('''
            INSERT INTO otp_codes (email, code, expires_at)
            VALUES (%s, %s, %s)
        ''', (email.lower(), code, expires_at))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Code OTP généré pour {email}")
        return True
    except Exception as e:
        print(f"❌ Erreur save_otp: {e}")
        return False

def verify_otp(email, code):
    """Vérifier un code OTP"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM otp_codes 
            WHERE email = %s 
            AND code = %s 
            AND expires_at > NOW() 
            AND used = FALSE
            ORDER BY created_at DESC
            LIMIT 1
        ''', (email.lower(), code))
        
        result = cursor.fetchone()
        
        if result:
            # Marquer le code comme utilisé
            cursor.execute('''
                UPDATE otp_codes 
                SET used = TRUE 
                WHERE id = %s
            ''', (result['id'],))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        
        cursor.close()
        conn.close()
        return False
    except Exception as e:
        print(f"❌ Erreur verify_otp: {e}")
        return False

def cleanup_old_otps():
    """Nettoyer les OTP expirés (appelé périodiquement)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM otp_codes 
            WHERE expires_at < NOW() - INTERVAL '1 day'
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur cleanup_old_otps: {e}")

def has_submitted(email):
    """Vérifier si un email a déjà soumis une idée"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM ideas WHERE email = %s', (email.lower(),))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result['count'] > 0
    except Exception as e:
        print(f"❌ Erreur has_submitted: {e}")
        return False

def save_idea(email, idea, category, timestamp):
    """Enregistrer une nouvelle idée"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ideas (email, idea, category, timestamp)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        ''', (email.lower(), idea, category, timestamp))
        
        idea_id = cursor.fetchone()['id']
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Idée #{idea_id} enregistrée pour {email}")
        return idea_id
    except Exception as e:
        print(f"❌ Erreur save_idea: {e}")
        raise

def get_all_ideas():
    """Récupérer toutes les idées"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM ideas ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        ideas = []
        for row in rows:
            idea_dict = dict(row)
            if idea_dict.get('timestamp'):
                idea_dict['timestamp'] = idea_dict['timestamp'].isoformat()
            if idea_dict.get('created_at'):
                idea_dict['created_at'] = idea_dict['created_at'].isoformat()
            ideas.append(idea_dict)
        
        return ideas
    except Exception as e:
        print(f"❌ Erreur get_all_ideas: {e}")
        return []

def get_ideas_by_category(category):
    """Récupérer les idées par catégorie"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM ideas 
            WHERE category = %s 
            ORDER BY created_at DESC
        ''', (category,))
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        ideas = []
        for row in rows:
            idea_dict = dict(row)
            if idea_dict.get('timestamp'):
                idea_dict['timestamp'] = idea_dict['timestamp'].isoformat()
            if idea_dict.get('created_at'):
                idea_dict['created_at'] = idea_dict['created_at'].isoformat()
            ideas.append(idea_dict)
        
        return ideas
    except Exception as e:
        print(f"❌ Erreur get_ideas_by_category: {e}")
        return []

def get_statistics():
    """Obtenir des statistiques sur les idées"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as total FROM ideas')
        total = cursor.fetchone()['total']
        
        cursor.execute('''
            SELECT category, COUNT(*) as count 
            FROM ideas 
            GROUP BY category 
            ORDER BY count DESC
        ''')
        categories = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            'total_ideas': total,
            'by_category': categories
        }
    except Exception as e:
        print(f"❌ Erreur get_statistics: {e}")
        return {
            'total_ideas': 0,
            'by_category': []
        }