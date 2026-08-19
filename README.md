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

## Prédiction par lot

La page **Prédiction par lot** permet d'importer un CSV contenant uniquement les cinq caractéristiques du modèle :

- `qualite_enseignement` (1 à 7) ;
- `charge_travail` (1 à 7) ;
- `interactivite` (1 à 7) ;
- `type_cours` (`présentiel`, `distanciel`, `hybride`) ;
- `niveau_etudiant` (`L1`, `L2`, `L3`, `M1`, `M2`).

Le fichier ne doit pas contenir la cible `satisfaction`. La validation est indépendante de celle du CSV d'entraînement : aucune colonne factice n'est ajoutée.

Le traitement est vectorisé avec le modèle actif et produit :

- la classe prédite `0/1` et son libellé ;
- `probability_satisfied` ;
- `probability_unsatisfied` ;
- la confiance de la classe prédite.

L'interface affiche un récapitulatif, les dix premières lignes et un bouton de téléchargement du CSV complet. Les exports temporaires sont isolés par utilisateur/session et les fichiers de plus de 24 heures sont nettoyés automatiquement. Un lot est limité à **5 Mo** et **5 000 lignes**.

Les prédictions par lot ne sont pas enregistrées automatiquement dans `StudentFeedback`, afin de ne pas mélanger une analyse de masse avec l'historique des prédictions individuelles utilisé par le tableau de bord et la page Statistiques.

## Gestion et comparaison des modèles

La page **Entraînement** permet désormais d'inspecter les modèles enregistrés avant de les activer :

- vérification de l'existence physique du fichier `.joblib` ;
- contrôle du format de l'artefact (pipeline actuel ou ancien format compatible) ;
- affichage d'Accuracy et, lorsqu'elles existent dans l'artefact, Precision, Recall et F1 ;
- activation d'un modèle historique sans réentraînement ;
- désactivation explicite du modèle actif ;
- garantie transactionnelle qu'un seul modèle peut être actif après une activation ;
- refus d'activation lorsqu'un fichier est absent, illisible ou incompatible.

Les anciens entraînements dont le fichier n'existe plus restent visibles comme historique mais ne peuvent pas être activés.

## Validation croisée et réglage automatique du MLP

Les nouveaux entraînements utilisent un protocole de sélection qui préserve un véritable jeu de test final :

1. le dataset validé est séparé une seule fois en **train 80 % / test final 20 %**, avec stratification ;
2. le **grid-search** est exécuté uniquement sur le train avec une validation croisée `StratifiedKFold` reproductible à 3 plis ;
3. quatre configurations sont comparées : couches `(64, 32)` ou `(128, 64, 32)`, avec `alpha=0.0001` ou `alpha=0.001` ;
4. le meilleur réglage est choisi selon le **F1-score moyen en validation croisée** ;
5. ce meilleur pipeline est réentraîné sur tout le train puis évalué **une seule fois** sur le test final qui n'a participé à aucun choix d'hyperparamètres.

L'artefact `.joblib` V3 enregistre les hyperparamètres retenus, les moyennes et écarts-types CV pour Accuracy/Precision/Recall/F1, ainsi que les résultats des quatre candidats. Les anciens artefacts V1/V2 restent compatibles et activables lorsqu'ils existent physiquement.

### Compatibilité des anciens artefacts scikit-learn

Les fichiers `.joblib` sont liés à la version de scikit-learn utilisée lors de leur entraînement. Lorsqu'un artefact a été sérialisé avec une autre version, l'application le conserve dans l'historique mais le marque **Version scikit-learn différente** et interdit son activation. Il doit être réentraîné avec l'environnement courant avant d'être utilisé.

## API REST V1

L'API est disponible sous `/api/v1/`.

### Authentification JWT

- `POST /api/v1/auth/token/` — obtient `access` et `refresh` ;
- `POST /api/v1/auth/token/refresh/` — renouvelle l'access token ;
- utiliser ensuite `Authorization: Bearer <access_token>`.

### Endpoints

- `POST /api/v1/predict/` — prédiction individuelle authentifiée ;
- `POST /api/v1/predict/batch/` — prédiction JSON vectorisée par lot ;
- `GET /api/v1/models/` — modèles, **staff uniquement** ;
- `GET /api/v1/feedbacks/` — prédictions enregistrées, **staff uniquement**, paginées ;
- `GET /api/v1/schema/` — schéma OpenAPI ;
- `GET /api/v1/docs/` — Swagger UI.

Les prédictions API ne sont pas automatiquement enregistrées dans `StudentFeedback`. Les endpoints réutilisent le moteur et le validateur de l'application web.

## UX et accessibilité — V14A

L'interface authentifiée propose maintenant trois préférences d'apparence : **Automatique**, **Clair** et **Sombre**. Le choix est conservé dans `localStorage` et le mode Automatique suit `prefers-color-scheme`.

V14A ajoute aussi un lien d'évitement vers le contenu principal, des styles `:focus-visible`, des cibles d'au moins 44 px pour les contrôles d'icône principaux, le respect de `prefers-reduced-motion`, un thème sombre pour les composants Bootstrap courants et un favicon servi également via `/favicon.ico`.

Cette étape améliore les fondations WCAG, mais ne prétend pas remplacer un audit navigateur complet avec axe/Lighthouse. Le profil utilisateur et la sécurité du compte sont traités en V14B, puis l'internationalisation FR/EN en V14C.

## Profil et sécurité du compte — V14B

V14B ajoute une section **Mon profil** basée sur l'utilisateur Django existant, sans nouveau modèle ni migration. L'utilisateur peut modifier son prénom, son nom et son adresse e-mail. Une modification de l'e-mail nécessite le mot de passe actuel et l'application refuse les doublons d'e-mail sans tenir compte de la casse.

Le changement de mot de passe utilise `PasswordChangeView` et `PasswordChangeForm` de Django. La session courante reste active après un changement réussi.

Le flux « Mot de passe oublié » utilise les vues de réinitialisation de Django avec lien à usage unique. En développement, si aucune configuration e-mail n'existe déjà, les messages sont écrits dans la console avec `console.EmailBackend`. En production, définir `EMAIL_BACKEND` et `DEFAULT_FROM_EMAIL` via l'environnement.

Le flux de réinitialisation conserve une réponse générique pour ne pas révéler si une adresse e-mail est enregistrée.

## RBAC — rôles et permissions V14B.1

L'application utilise désormais un contrôle d'accès basé sur les rôles :

- **Super Administrateur** : compte Django `is_superuser=True`, accès absolu ;
- **Administrateur** : gestion des comptes, données, modèles, statistiques et accès staff ;
- **Responsable ML** : entraînement, activation/comparaison des modèles, données et statistiques ;
- **Analyste** : prédiction individuelle et par lot, données, exports et statistiques ;
- **Utilisateur** : prédiction individuelle, notifications et profil personnel.

Les quatre rôles métier sont des groupes Django et reçoivent des permissions explicites. Les routes sensibles sont aussi contrôlées côté serveur par middleware ou permissions DRF ; masquer un bouton n'est donc pas considéré comme une protection.

La commande `python manage.py setup_roles` recrée de façon idempotente les groupes et permissions. L'option `--promote-superuser <username>` permet de confirmer explicitement un Super Administrateur sans modifier son mot de passe.

Les Super Administrateurs sont protégés contre les modifications de rôle depuis l'interface métier. Pour créer ou modifier un superuser, utiliser `createsuperuser`, la CLI Django ou l'administration Django avec un compte superuser.

## Internationalisation FR / EN — V14C.1

L'application utilise désormais l'infrastructure i18n native de Django avec `LocaleMiddleware`, la route `set_language`, une langue source française et un catalogue anglais compilé. Le choix FR/EN est conservé par Django et suit la navigation.

Cette première étape couvre le shell global, les contrôles de thème, le profil, la sécurité du compte et l'administration RBAC. Les noms internes des groupes Django restent stables en français, tandis que leurs libellés d'affichage sont traduits selon la langue active.

Direction visuelle : « Academic Control Room ». L'identité académique existante est conservée avec un traitement plus éditorial des titres et un sélecteur de langue compact, accessible et cohérent avec le thème clair/sombre.

V14C.2 traduira ensuite les écrans métier Predictor (Accueil, Prédiction, Batch, Entraînement, Données, Statistiques), leurs messages Python et le JavaScript spécifique.

## Internationalisation Predictor — V14C.2

V14C.2 étend la traduction FR/EN aux écrans métier : Dashboard, prédiction individuelle, prédiction par lot, entraînement, comparaison de modèles, gestion des données, statistiques et explications de prédiction.

Les valeurs métier stockées en base ou dans les artefacts ne sont pas renommées. Un filtre de template traduit uniquement leur libellé d'affichage (`Présentiel`, `Satisfait`, états d'artefacts, etc.), ce qui évite de casser les comparaisons, les exports, l'API ou le modèle ML.

La passe frontend poursuit la direction « Academic Control Room » : titres éditoriaux, tableaux plus lisibles, densité maîtrisée, cartes et formulaires harmonisés, sans remplacer l'identité existante par un thème générique.

---
## Production, CI et démonstration portfolio — V17

Le projet dispose maintenant d'un socle de production avec PostgreSQL configurable, Gunicorn, WhiteNoise, health-check, variables d'environnement fail-closed et CI GitHub Actions.

Un modèle ML Pipeline v3 est livré dans `deployment/model/` avec son manifeste SHA-256. La commande suivante vérifie l'intégrité de la release locale :

```powershell
python .\scripts\verify_release.py
```

Pour un déploiement neuf, après les migrations :

```powershell
python manage.py setup_roles
python manage.py bootstrap_portfolio
```

Le compte portfolio est volontairement public mais limité au rôle `Utilisateur` et à la prédiction individuelle. Ses prédictions ne sont pas persistées dans `StudentFeedback`, afin de ne pas fausser les statistiques du projet.

La procédure complète de production, les variables d'environnement, le bootstrap, la création du compte administrateur et les contrôles post-déploiement sont documentés dans `DEPLOYMENT.md`.
