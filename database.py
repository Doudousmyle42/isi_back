import sqlite3
from datetime import datetime
import json

DB_NAME = 'isi_ideas.db'

def get_connection():
    """Créer une connexion à la base de données"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Pour récupérer les résultats comme des dictionnaires
    return conn

def init_db():
    """Initialiser la base de données"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            idea TEXT NOT NULL,
            category TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de données initialisée")

def has_submitted(email):
    """Vérifier si un email a déjà soumis une idée"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM ideas WHERE email = ?', (email,))
    result = cursor.fetchone()
    conn.close()
    
    return result['count'] > 0

def save_idea(email, idea, category, timestamp):
    """Enregistrer une nouvelle idée"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO ideas (email, idea, category, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (email, idea, category, timestamp))
    
    idea_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"✅ Idée #{idea_id} enregistrée pour {email}")
    return idea_id

def get_all_ideas():
    """Récupérer toutes les idées"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM ideas ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    ideas = [dict(row) for row in rows]
    return ideas

def get_ideas_by_category(category):
    """Récupérer les idées par catégorie"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM ideas 
        WHERE category = ? 
        ORDER BY created_at DESC
    ''', (category,))
    rows = cursor.fetchall()
    conn.close()
    
    ideas = [dict(row) for row in rows]
    return ideas

def get_statistics():
    """Obtenir des statistiques sur les idées"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total d'idées
    cursor.execute('SELECT COUNT(*) as total FROM ideas')
    total = cursor.fetchone()['total']
    
    # Idées par catégorie
    cursor.execute('''
        SELECT category, COUNT(*) as count 
        FROM ideas 
        GROUP BY category 
        ORDER BY count DESC
    ''')
    categories = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'total_ideas': total,
        'by_category': categories
    }

def export_to_json(filename='ideas_export.json'):
    """Exporter toutes les idées en JSON"""
    ideas = get_all_ideas()
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(ideas, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(ideas)} idées exportées vers {filename}")
    return filename



