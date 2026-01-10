from database import get_all_ideas, get_statistics, export_to_json
import csv
from datetime import datetime

def export_to_csv(filename='idees_export.csv'):
    """Exporter toutes les idées en CSV"""
    ideas = get_all_ideas()
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Email', 'Catégorie', 'Idée', 'Date de soumission'])
        
        for idea in ideas:
            writer.writerow([
                idea['id'],
                idea['email'],
                idea['category'],
                idea['idea'],
                idea['timestamp']
            ])
    
    print(f"✅ {len(ideas)} idées exportées vers {filename}")

def show_statistics():
    """Afficher les statistiques"""
    stats = get_statistics()
    print("\n📊 STATISTIQUES")
    print(f"Total d'idées: {stats['total_ideas']}")
    print("\nPar catégorie:")
    for cat in stats['by_category']:
        print(f"  - {cat['category']}: {cat['count']} idées")

if __name__ == '__main__':
    print("🎯 Export des idées ISI\n")
    
    # Afficher les stats
    show_statistics()
    
    # Exporter en CSV
    export_to_csv(f'idees_isi_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    
    # Exporter en JSON
    export_to_json(f'idees_isi_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')