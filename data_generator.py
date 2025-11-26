# data_generator.py
import pandas as pd
import numpy as np
from datetime import datetime
import os

def generate_synthetic_data(n_samples=1000, save_to_file=True, use_new_scale=True):
    """
    Génère des données synthétiques pour la satisfaction des étudiants avec une logique de scoring corrigée.
    """
    np.random.seed(42)
    
    data = []
    
    for i in range(n_samples):
        # Utilisation de l'échelle 1-7 (nouvelle échelle)
        qualite_enseignement = np.clip(np.round(np.random.normal(4, 1.2)), 1, 7).astype(int)
        interactivite_base = qualite_enseignement + np.random.normal(0, 0.8)
        interactivite = np.clip(np.round(interactivite_base), 1, 7).astype(int)
        charge_travail = np.clip(np.round(np.random.gamma(1.5, 2) + 2), 1, 7).astype(int)

        # Type de cours et niveau
        type_cours = np.random.choice(['présentiel', 'distanciel', 'hybride'], p=[0.5, 0.3, 0.2])
        niveau_etudiant = np.random.choice(['L1', 'L2', 'L3'], p=[0.4, 0.35, 0.25])
        
        # ======================================================================
        # ✨ CORRECTION MAJEURE : Logique de calcul de la satisfaction revue ✨
        # Le score est maintenant basé sur une pondération logique sur 100 points.
        # ======================================================================
        
        satisfaction_score = 0
        
        # 50 points pour la qualité de l'enseignement
        # La formule ((valeur - 1) / 6) normalise une note de 1-7 sur une échelle de 0-1
        satisfaction_score += ((qualite_enseignement - 1) / 6) * 50
        
        # 30 points pour l'interactivité
        satisfaction_score += ((interactivite - 1) / 6) * 30
        
        # 20 points pour la charge de travail (une charge modérée est idéale)
        # Une charge de 4/7 donne le maximum de points, les extrêmes (1 ou 7) en donnent 0.
        charge_score = 1 - (abs(charge_travail - 4) / 3)
        satisfaction_score += charge_score * 20
        
        # Bonus / Malus
        if type_cours == 'présentiel':
            satisfaction_score += 5  # Bonus pour le présentiel
        elif type_cours == 'distanciel':
            satisfaction_score -= 5  # Malus pour le distanciel
            
        if niveau_etudiant == 'L3' and qualite_enseignement < 4:
            satisfaction_score -= 5  # Les L3 sont plus exigeants sur la qualité
        elif niveau_etudiant == 'L1':
            satisfaction_score += 3  # Les L1 sont souvent plus faciles à satisfaire
            
        # Ajout d'un bruit aléatoire pour plus de réalisme
        satisfaction_score += np.random.normal(0, 5)
        
        # On s'assure que le score reste entre 0 et 100
        satisfaction_score = np.clip(satisfaction_score, 0, 100)
        
        # Seuil de satisfaction : un score au-dessus de 50 est considéré comme "satisfait"
        satisfaction_threshold = 50
        satisfaction = 1 if satisfaction_score >= satisfaction_threshold else 0
        
        data.append({
            'qualite_enseignement': qualite_enseignement,
            'charge_travail': charge_travail,
            'interactivite': interactivite,
            'type_cours': type_cours,
            'niveau_etudiant': niveau_etudiant,
            'satisfaction': satisfaction
        })
    
    df = pd.DataFrame(data)
    
    if save_to_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"avis_etudiants_{timestamp}.csv"
        df.to_csv(filename, index=False)
        print(f"Données sauvegardées dans {filename}")
        print(f"Taille du dataset: {len(df)} échantillons")
        print(f"Distribution de satisfaction: {df['satisfaction'].value_counts(normalize=True).to_dict()}")
    
    return df

if __name__ == "__main__":
    df = generate_synthetic_data(1000, use_new_scale=True)
    print("\n Aperçu des données corrigées:")
    print(df.head(10))
    print("\n Statistiques descriptives:")
    print(df.describe())