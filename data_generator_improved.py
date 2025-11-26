# data_generator_improved.py
"""
Générateur de données synthétiques AMÉLIORÉ pour la satisfaction étudiante
- Échelle cohérente 1-7 pour tous les critères
- Logique de satisfaction réaliste et équilibrée
- Données corrélées de manière logique
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

def generate_realistic_data(n_samples=1000, save_to_file=True, filename=None):
    """
    Génère des données réalistes avec une logique de satisfaction cohérente.
    
    Paramètres:
    -----------
    n_samples : int
        Nombre d'échantillons à générer
    save_to_file : bool
        Si True, sauvegarde dans un fichier CSV
    filename : str
        Nom du fichier (si None, génère un nom avec timestamp)
    """
    np.random.seed(42)
    
    data = []
    
    # Compteurs pour équilibrer les classes
    satisfied_count = 0
    unsatisfied_count = 0
    target_satisfaction_rate = 0.65  # 65% de satisfaction (réaliste)
    
    for i in range(n_samples):
        # ==========================================
        # 1. GÉNÉRATION DES CARACTÉRISTIQUES DE BASE
        # ==========================================
        
        # Qualité d'enseignement : distribution normale centrée sur 4.5
        qualite_enseignement = np.clip(
            np.round(np.random.normal(4.5, 1.2)), 1, 7
        ).astype(int)
        
        # Interactivité : corrélée avec la qualité (bon prof = plus interactif)
        interactivite_base = qualite_enseignement + np.random.normal(0, 0.9)
        interactivite = np.clip(
            np.round(interactivite_base), 1, 7
        ).astype(int)
        
        # Charge de travail : distribution gamma (plus de valeurs moyennes)
        charge_travail = np.clip(
            np.round(np.random.gamma(2, 1.5) + 2), 1, 7
        ).astype(int)
        
        # Type de cours : distribution réaliste
        type_cours = np.random.choice(
            ['présentiel', 'distanciel', 'hybride'], 
            p=[0.55, 0.25, 0.20]
        )
        
        # Niveau étudiant
        niveau_etudiant = np.random.choice(
            ['L1', 'L2', 'L3'], 
            p=[0.40, 0.35, 0.25]
        )
        
        # ==========================================
        # 2. CALCUL DU SCORE DE SATISFACTION
        # ==========================================
        
        score = 0
        
        # A) Qualité de l'enseignement (40 points max)
        # C'est le facteur le plus important
        score += ((qualite_enseignement - 1) / 6) * 40
        
        # B) Interactivité (30 points max)
        # Deuxième facteur d'importance
        score += ((interactivite - 1) / 6) * 30
        
        # C) Charge de travail (20 points max)
        # Une charge optimale est autour de 4/7
        # Trop léger (1-2) ou trop lourd (6-7) = mauvais
        charge_optimale = 4
        distance_optimale = abs(charge_travail - charge_optimale)
        charge_score = max(0, 1 - (distance_optimale / 3))
        score += charge_score * 20
        
        # D) Bonus/Malus selon le type de cours (10 points max)
        if type_cours == 'présentiel':
            score += 8  # Les étudiants préfèrent généralement le présentiel
        elif type_cours == 'hybride':
            score += 5  # Bon compromis
        else:  # distanciel
            score += 2  # Moins apprécié en général
        
        # E) Ajustements selon le niveau
        if niveau_etudiant == 'L1':
            # Les L1 sont généralement plus tolérants
            score += 3
        elif niveau_etudiant == 'L3':
            # Les L3 sont plus exigeants
            if qualite_enseignement < 4:
                score -= 5
            # Mais apprécient la charge de travail modérée à élevée
            if charge_travail >= 5:
                score += 2
        
        # F) Facteurs d'interaction
        # Un cours de mauvaise qualité MAIS très interactif peut compenser
        if qualite_enseignement <= 3 and interactivite >= 5:
            score += 5
        
        # Un cours excellent mais trop lourd peut décevoir
        if qualite_enseignement >= 6 and charge_travail >= 6:
            score -= 3
        
        # Distanciel avec faible interactivité = très mauvais
        if type_cours == 'distanciel' and interactivite <= 3:
            score -= 5
        
        # G) Ajout de bruit réaliste (variance individuelle)
        score += np.random.normal(0, 4)
        
        # H) Normalisation du score entre 0 et 100
        score = np.clip(score, 0, 100)
        
        # ==========================================
        # 3. DÉTERMINATION DE LA SATISFACTION
        # ==========================================
        
        # Seuil adaptatif pour atteindre le taux cible
        current_rate = satisfied_count / (i + 1) if i > 0 else 0
        
        # Seuil de base
        base_threshold = 55
        
        # Ajustement dynamique pour atteindre le taux cible
        if current_rate < target_satisfaction_rate - 0.05:
            # On est en dessous du taux cible, on facilite la satisfaction
            threshold = base_threshold + 3
        elif current_rate > target_satisfaction_rate + 0.05:
            # On est au-dessus, on durcit un peu
            threshold = base_threshold - 3
        else:
            threshold = base_threshold
        
        # Décision finale
        satisfaction = 1 if score >= threshold else 0
        
        if satisfaction == 1:
            satisfied_count += 1
        else:
            unsatisfied_count += 1
        
        # ==========================================
        # 4. AJOUT À LA BASE DE DONNÉES
        # ==========================================
        
        data.append({
            'qualite_enseignement': qualite_enseignement,
            'charge_travail': charge_travail,
            'interactivite': interactivite,
            'type_cours': type_cours,
            'niveau_etudiant': niveau_etudiant,
            'satisfaction': satisfaction
        })
    
    # ==========================================
    # 5. CRÉATION DU DATAFRAME
    # ==========================================
    
    df = pd.DataFrame(data)
    
    # Statistiques finales
    stats = {
        'total': len(df),
        'satisfaits': satisfied_count,
        'non_satisfaits': unsatisfied_count,
        'taux_satisfaction': (satisfied_count / len(df)) * 100,
        'qualite_moyenne': df['qualite_enseignement'].mean(),
        'charge_moyenne': df['charge_travail'].mean(),
        'interactivite_moyenne': df['interactivite'].mean()
    }
    
    print("\n" + "="*60)
    print("📊 STATISTIQUES DU DATASET GÉNÉRÉ")
    print("="*60)
    print(f"Total d'échantillons    : {stats['total']}")
    print(f"Satisfaits              : {stats['satisfaits']} ({stats['taux_satisfaction']:.1f}%)")
    print(f"Non satisfaits          : {stats['non_satisfaits']} ({100-stats['taux_satisfaction']:.1f}%)")
    print(f"\nQualité moyenne         : {stats['qualite_moyenne']:.2f}/7")
    print(f"Charge moyenne          : {stats['charge_moyenne']:.2f}/7")
    print(f"Interactivité moyenne   : {stats['interactivite_moyenne']:.2f}/7")
    print("="*60)
    
    # Distribution par type de cours
    print("\n📌 DISTRIBUTION PAR TYPE DE COURS:")
    type_stats = df.groupby('type_cours')['satisfaction'].agg(['count', 'sum', 'mean'])
    type_stats.columns = ['Total', 'Satisfaits', 'Taux']
    type_stats['Taux'] = (type_stats['Taux'] * 100).round(1)
    print(type_stats)
    
    # Distribution par niveau
    print("\n🎓 DISTRIBUTION PAR NIVEAU:")
    niveau_stats = df.groupby('niveau_etudiant')['satisfaction'].agg(['count', 'sum', 'mean'])
    niveau_stats.columns = ['Total', 'Satisfaits', 'Taux']
    niveau_stats['Taux'] = (niveau_stats['Taux'] * 100).round(1)
    print(niveau_stats)
    
    # ==========================================
    # 6. SAUVEGARDE DU FICHIER
    # ==========================================
    
    if save_to_file:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"satisfaction_etudiants_{n_samples}_{timestamp}.csv"
        
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"\n✅ Données sauvegardées dans : {filename}")
        print(f"📁 Taille du fichier : {os.path.getsize(filename) / 1024:.2f} KB")
    
    return df, stats


def generate_multiple_datasets():
    """
    Génère plusieurs datasets de tailles différentes pour l'entraînement.
    """
    sizes = [500, 1000, 2000]
    
    print("\n🚀 GÉNÉRATION DE PLUSIEURS DATASETS...")
    print("="*60)
    
    for size in sizes:
        print(f"\n📦 Génération de {size} échantillons...")
        df, stats = generate_realistic_data(n_samples=size, save_to_file=True)
        print(f"✅ Dataset de {size} échantillons créé avec succès!")
    
    print("\n" + "="*60)
    print("✨ Tous les datasets ont été générés avec succès!")
    print("="*60)


def analyze_existing_csv(filepath):
    """
    Analyse un fichier CSV existant pour vérifier sa cohérence.
    """
    try:
        df = pd.read_csv(filepath)
        
        print("\n" + "="*60)
        print(f"🔍 ANALYSE DU FICHIER : {filepath}")
        print("="*60)
        
        print("\n📋 Colonnes détectées:")
        print(df.columns.tolist())
        
        print("\n📊 Statistiques descriptives:")
        print(df.describe())
        
        print("\n🎯 Distribution de la satisfaction:")
        if 'satisfaction' in df.columns:
            sat_counts = df['satisfaction'].value_counts()
            print(sat_counts)
            print(f"\nTaux de satisfaction : {(sat_counts.get(1, 0) / len(df)) * 100:.1f}%")
        
        print("\n⚠️ Valeurs manquantes:")
        print(df.isnull().sum())
        
        print("\n📏 Plages de valeurs:")
        for col in ['qualite_enseignement', 'charge_travail', 'interactivite']:
            if col in df.columns:
                print(f"{col:25} : {df[col].min()} - {df[col].max()}")
        
        return df
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse : {str(e)}")
        return None


# ==========================================
# POINT D'ENTRÉE PRINCIPAL
# ==========================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎓 GÉNÉRATEUR DE DONNÉES - SATISFACTION ÉTUDIANTE")
    print("="*60)
    
    # Menu interactif
    print("\nQue souhaitez-vous faire ?")
    print("1. Générer un dataset de 1000 échantillons")
    print("2. Générer plusieurs datasets (500, 1000, 2000)")
    print("3. Analyser un CSV existant")
    print("4. Générer un dataset personnalisé")
    
    try:
        choice = input("\nVotre choix (1-4) : ").strip()
        
        if choice == "1":
            df, stats = generate_realistic_data(n_samples=1000, save_to_file=True)
            print("\n✨ Dataset de 1000 échantillons généré avec succès!")
            
        elif choice == "2":
            generate_multiple_datasets()
            
        elif choice == "3":
            filepath = input("Chemin du fichier CSV : ").strip()
            analyze_existing_csv(filepath)
            
        elif choice == "4":
            n = int(input("Nombre d'échantillons à générer : ").strip())
            df, stats = generate_realistic_data(n_samples=n, save_to_file=True)
            print(f"\n✨ Dataset de {n} échantillons généré avec succès!")
            
        else:
            print("❌ Choix invalide. Génération d'un dataset par défaut...")
            df, stats = generate_realistic_data(n_samples=1000, save_to_file=True)
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Opération annulée par l'utilisateur.")
    except Exception as e:
        print(f"\n❌ Erreur : {str(e)}")
        print("Génération d'un dataset par défaut...")
        df, stats = generate_realistic_data(n_samples=1000, save_to_file=True)
    
    print("\n👋 Merci d'avoir utilisé le générateur de données!")
    print("="*60 + "\n")