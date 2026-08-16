# Classification de satisfaction étudiante

Projet de contrôle terminal d'intelligence artificielle : classification binaire de la satisfaction d'un étudiant à partir de caractéristiques d'un cours, avec un réseau de neurones MLP et une interface Django.

## Fonctionnalités

- prédiction satisfait / non satisfait avec probabilité ;
- entraînement d'un MLP depuis un CSV ;
- validation et prétraitement des données ;
- historique des entraînements ;
- statistiques descriptives et graphiques ;
- gestion, modification, suppression et export des prédictions enregistrées ;
- authentification Django.

## Installation sous PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

L'application est ensuite disponible sur `http://127.0.0.1:8000/`.

## Configuration locale

Par défaut, le projet reste utilisable en développement. Pour fournir une clé différente :

```powershell
$env:DJANGO_SECRET_KEY="une-cle-secrete-longue-et-unique"
```

Pour modifier les hôtes autorisés :

```powershell
$env:DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1"
```

Pour désactiver le mode debug :

```powershell
$env:DJANGO_DEBUG="0"
```

## Données d'entraînement

Colonnes attendues :

- `qualite_enseignement` : entier 1 à 7 ;
- `charge_travail` : entier 1 à 7 ;
- `interactivite` : entier 1 à 7 ;
- `type_cours` : `présentiel`, `distanciel` ou `hybride` ;
- `niveau_etudiant` : `L1`, `L2`, `L3`, `M1` ou `M2` ;
- `satisfaction` : `0` ou `1`.

Le pipeline sépare les données train/test avant d'ajuster les transformations afin d'éviter la fuite de données.

## Génération des données synthétiques

Le projet contient `generate_synthetic_data.py`, qui produit des données reproductibles avec des distributions plausibles et les cinq niveaux académiques.

Exemple pour générer 2 000 avis :

```powershell
python .\generate_synthetic_data.py --rows 2000 --seed 42
```

Le fichier est créé par défaut dans :

```text
data\satisfaction_etudiants_synthetiques_v8_2000.csv
```

Le générateur utilise des profils de caractéristiques uniques, une distribution pondérée pour les notes, types de cours et niveaux, puis une probabilité de satisfaction dépendant notamment de la qualité, de l'interactivité et de la charge de travail, avec une variabilité aléatoire contrôlée.

## Validation des données enregistrées

Les valeurs 1–7, les types de cours, les niveaux `L1/L2/L3/M1/M2` et la probabilité 0–100 sont protégés par des validateurs Django et des contraintes en base de données.

## Validation

```powershell
python manage.py check
python manage.py test
```

## Interprétabilité du modèle

Le projet fournit deux niveaux d'explication du MLP actif :

- **importance globale par permutation** : mesure la baisse moyenne du F1-score lorsque chacune des cinq caractéristiques métier est mélangée ;
- **explication locale par valeurs de Shapley exactes** : pour une prédiction individuelle, répartit la différence entre la probabilité de référence et `P(satisfait)` entre `qualite_enseignement`, `charge_travail`, `interactivite`, `type_cours` et `niveau_etudiant`.

Comme le problème ne comporte que cinq caractéristiques, les `2^5 = 32` coalitions peuvent être évaluées directement. Cette implémentation ne dépend donc pas du paquet externe `shap` et travaille sur les variables métier brutes du pipeline scikit-learn.

Les nouveaux entraînements enregistrent dans l'artefact joblib un petit `explanation_background` issu du train et le hold-out `explanation_reference` issu du test. Pour les artefacts V8 déjà existants, l'application utilise automatiquement le dataset synthétique V8 local comme référence de secours.

Ces explications décrivent le comportement prédictif du modèle et ne doivent pas être interprétées comme des effets causaux.
