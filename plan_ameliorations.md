# Plan d’implémentation détaillé – Améliorations du Student Satisfaction Project

**Version** : 2.0  
**Date** : 2026-08-16  
**Auteur** : Claude Code (Fable 5)  

Ce document décrit, étape par étape, la mise en œuvre complète de **tous** les axes d’amélioration suivants :

1. **Interprétabilité des prédictions** (importance globale + explication SHAP par prédiction)  
2. **Prédiction par lot** (upload CSV → prédictions multiples + récapitulatif)  
3. **Gestion avancée des modèles** (activation/désactivation, comparaison, validation croisée, réglage d’hyperparamètres)  
4. **API REST / intégration externe** (endpoints JWT/DRF, documentation OpenAPI)  
5. **Expérience utilisateur & accessibilité** (thème sombre/clair, i18n complet, améliorations WCAG, profil utilisateur, réinitialisation de mot de passe)  
6. **DevOps & qualité du code** (GitHub Actions, linting/formatage, couverture de tests, health‑checks, versionning sémantique)  
7. **Fonctionnalités pédagogiques / communautaires** (explications textuelles automatiques, forum/commentaires, badges/gamification, espace de partage de jeux de données synthétiques)  

Chaque axe est découpé en tâches atomiques, avec les fichiers à modifier, les extraits de code clés, les commandes à exécuter, les tests à ajouter/mettre à jour et les points de validation.

---

## 1. Interprétabilité des prédictions

### 1.1 Objectifs
- Afficher, dans la page de statistiques, l’importance moyenne de chaque caractéristique (qualité, charge, interactivité, type cours, niveau) sur le modèle actif.  
- Dans la page de prédiction individuelle, montrer une explication locale (valeurs SHAP) sous forme de barre horizontale ou de texte simple indiquant la contribution de chaque caractéristique à la décision du modèle.  

### 1.2 Prérequis
- Ajouter le paquet `shap` (ou `lime`) au `requirements.txt`.  
- S’assurer que le modèle actif est toujours chargé sous forme de pipeline scikit‑learn (déjà le cas).  

### 1.3 Tâches

| # | Tâche | Fichiers concernés | Détails / Code | Validation |
|---|-------|-------------------|----------------|------------|
| 1 | Ajouter dépendance SHAP | `requirements.txt` | `shap==0.45.1` | `pip install -r requirements.txt` réussie |
| 2 | Utilitaire d’explication globale | `predictor/utils_explain.py` (nouveau) | ```python\nimport shap\nimport numpy as np\nfrom .neural_network_model import load_current_model, FEATURE_COLUMNS\n\ndef get_global_importance(model_data=None):\n    if model_data is None:\n        model_data = load_current_model()\n    if model_data is None or 'pipeline' not in model_data:\n        return None\n    pipeline = model_data['pipeline']\n    preprocessor = pipeline.named_steps['preprocessor']\n    classifier = pipeline.named_steps['classifier']\n    from sklearn.inspection import permutation_importance\n    import pandas as pd\n    reference = pd.DataFrame({f: [4]*10 for f in FEATURE_COLUMNS})\n    result = permutation_importance(classifier, preprocessor.transform(reference), np.ones(10), n_repeats=5, random_state=0)\n    importances = result.importances_mean\n    return dict(zip(FEATURE_COLUMNS, importances))\n``` | - Le fichier est importable sans erreur.<br>- Fonction retourne un dict avec 5 clés. |
| 3 | Intégrer l’importance globale dans la vue `statistics` | `predictor/views.py` | - Importer `get_global_importance` en haut.<br>- Dans la vue `statistics`, après le calcul de `charts_data`, appeler `global_imp = get_global_importance(model_data)` et l’ajouter au contexte sous `"global_importance"`.<br>- Passer ce dictionnaire au template. | - Après refresh de `/statistics/`, la variable `global_importance` apparaît dans le contexte. |
| 4 | Modifier le template `statistics.html` pour afficher l’importance | `template/predictor/statistics.html` | Ajouter une section :\n```html\n{% if global_importance %}\n<div class=\"card mb-4\">\n  <div class=\"card-header\">Importance globale des caractéristiques</div>\n  <div class=\"card-body\">\n    <ul class=\"list-group\">\n      {% for feat, imp in global_importance.items %}\n        <li class=\"list-group-item d-flex justify-content-between align-items-center\">\n          {{ feat|title }}\n          <span class=\"badge bg-primary rounded-pill\">{{ imp|floatformat:3 }}</span>\n        </li>\n      {% endfor %}\n    </ul>\n  </div>\n</div>\n{% endif %}\n``` | - La section s’affiche correctement avec des valeurs numériques. |
| 5 | Utilitaire d’explication SHAP locale (par prédiction) | Même `utils_explain.py` | ```python\nimport shap\nimport pandas as np\n\ndef get_shap_explanation(model_data, input_dict):\n    if model_data is None or 'pipeline' not in model_data:\n        return None\n    pipeline = model_data['pipeline']\n    input_df = pd.DataFrame([input_dict], columns=FEATURE_COLUMNS)\n    background = pipeline.named_steps['preprocessor'].transform(\n        pd.DataFrame({f: [4]*50 for f in FEATURE_COLUMNS})\n    )\n    explainer = shap.KernelExplainer(pipeline.predict, background, link=\"logit\")\n    shap_values = explainer.shap_values(input_df)\n    pred_class = int(pipeline.predict(input_df)[0])\n    values = shap_values[pred_class][0]\n    return dict(zip(FEATURE_COLUMNS, values.tolist()))\n``` | - Fonction testable hors Django (unit test). |
| 6 | Modifier la vue `predict` pour ajouter l’explication locale | `predictor/views.py` | - Après obtention de `prediction_result`, appeler `explanation = get_shap_explanation(model_data, input_data)`.<br>- Ajouter `explanation` au contexte du rendu (`"explanation": explanation`).<br>- Gérer le cas où l’explication est None (afficher un message). | - La variable `explanation` apparaît dans le contexte après soumission du formulaire. |
| 7 | Modifier le template `predict.html` pour afficher l’explication | `template/predictor/predict.html` | Ajouter sous le résultat de prédiction :\n```html\n{% if explanation %}\n<div class=\"card mt-4\">\n  <div class=\"card-header\">Explication de la prédiction (SHAP)</div>\n  <div class=\"card-body\">\n    <div class=\"row\">\n      {% for feat, val in explanation.items %}\n        <div class=\"col-md-4 mb-2\">\n          <div class=\"progress\">\n            <div class=\"progress-bar {% if val >= 0 %}bg-success{% else %}bg-danger{% endif %}\" role=\"progressbar\" style=\"width: {{ (val|abs)*10|floatformat:0 }}%;\" aria-valuenow=\"{{ (val|abs)*10|floatformat:0 }}\" aria-valuemin=\"0\" aria-valuemax=\"100\">\n              {{ feat|title }}: {{ val|floatformat:3 }}\n            </div>\n          </div>\n        </div>\n      {% endfor %}\n    </div>\n    <p class=\"mt-2\"><small>Valeur positive → augmente la probabilité d’être satisfait ; négative → diminue.</small></p>\n  </div>\n</div>\n{% endif %}\n``` | - L’explication s’affiche sous forme de barres de progression colorées. |
| 8 | Écrire des tests unitaires pour les utilitaires d’explication | `predictor/tests.py` (ajouter une nouvelle classe `ExplanationTests`) | - Tester `get_global_importance` avec un modèle factice.<br>- Tester `get_shap_explanation` avec une entrée connue et vérifier que la somme des valeurs approx. égale à la différence de log‑odds (facultatif). | - `python manage.py test predictor` passe. |
| 9 | Mettre à jour le fichier `README.md` pour documenter la nouvelle fonctionnalité | `README.md` | Ajouter une sous‑section « Interprétabilité des prédictions » sous Fonctionnalités. | - README reflète les changements. |

### 1.4 Ordre d’exécution recommandé
1. Ajout dépendance (req).  
2. Création du fichier `utils_explain.py` + tests unitaires.  
3. Intégration globale (views + template).  
4. Intégration locale (views + template).  
5. Documentation.  

Chaque étape doit être validée en lançant le serveur de développement et en vérifiant l’affichage.

### 1.5 Points de vigilance
- SHAP peut être lent sur de gros jeux de données ; on utilise un petit jeu de référence (50‑100 lignes) stocké en mémoire ou sérialisé. En production, envisager de pré‑calculer un échantillon représentatif du jeu d’entraînement et de le sauvegarder avec le modèle (ajouter un champ `background` dans l’artefact joblib).  
- Pour éviter les erreurs de sérialisation, ne pas stocker l’explainer SHAP dans le modèle, seulement le background.  
- Vérifier que les valeurs retournées sont bien des floats (pas de objects numpy) pour le rendu JSON dans les templates.

---

## 2. Prédiction par lot

### 2.1 Objectifs
- Autoriser l’import d’un fichier CSV contenant plusieurs lignes (mêmes caractéristiques que l’entraînement) et retourner un CSV contenant les prédictions + probabilités.  
- Après génération, fournir un petit récapitulatif (taux de satisfaction moyen, répartition par caractéristique) directement dans l’interface, sans quitter la page.  

### 2.2 Prérequis
- Le formulaire d’upload doit accepter les fichiers `.csv`.  
- Utiliser `pandas` pour lire et écrire le CSV (déjà présent).  

### 2.3 Tâches

| # | Tâche | Fichiers | Détails / Code | Validation |
|---|-------|----------|----------------|------------|
| 1 | Créer une nouvelle vue `batch_predict` | `predictor/views.py` | ```python\n@login_required(login_url='login_register')\ndef batch_predict(request):\n    if request.method == 'POST' and request.FILES.get('csv_file'):\n        csv_file = request.FILES['csv_file']\n        if not csv_file.name.lower().endswith('.csv'):\n            messages.error(request, 'Le fichier doit être au format CSV.')\n            return redirect('batch_predict')\n        try:\n            df = pd.read_csv(csv_file, encoding='utf-8-sig')\n            from .neural_network_model import validate_training_dataframe, FEATURE_COLUMNS\n            df['satisfaction'] = 0  # valeur temporaire\n            validated = validate_training_dataframe(df)\n            validated = validated[FEATURE_COLUMNS]\n            from .neural_network_model import load_current_model, predict_satisfaction\n            model_data = load_current_model()\n            if model_data is None:\n                messages.error(request, 'Aucun modèle actif.Entraînez d\'abord un modèle.')\n                return redirect('batch_predict')\n            preds = []\n            probs = []\n            for _, row in validated.iterrows():\n                input_data = row.to_dict()\n                res = predict_satisfaction(model_data, input_data)\n                preds.append(res['prediction'])\n                probs.append(res['probability_satisfied'])\n            validated['predicted_satisfaction'] = preds\n            validated['probability_satisfied'] = probs\n            response = HttpResponse(content_type='text/csv; charset=utf-8')\n            response['Content-Disposition'] = 'attachment; filename=\"predictions_lot.csv\"'\n            validated.to_csv(response, index=False, encoding='utf-8-sig')\n            notify_user(request.user, 'Prédiction par lot terminée', f'{len(validated)} lignes traitées.', level='success', event_type='prediction', target_url=reverse('batch_predict'))\n            messages.success(request, f'Prédiction terminée pour {len(validated)} enregistrements.')\n            return response\n        except Exception as e:\n            logger.exception('Erreur lors de la prédiction par lot')\n            messages.error(request, f'Erreur de traitement : {e}')\n            return redirect('batch_predict')\n    else:\n        return render(request, 'predictor/batch_predict.html')\n``` | - La vue accepte GET (affiche formulaire) et POST (traite). |
| 2 | Créer l’URL associée | `predictor/urls.py` | - `path('batch-predict/', views.batch_predict, name='batch_predict'),` | - `reverse('batch_predict')` fonctionne. |
| 3 | Créer le template `batch_predict.html` (reprenant le style du formulaire d’entraînement) | `template/predictor/batch_predict.html` | - Étendre `base.html`.<br>- Formulaire avec `<input type=\"file\" name=\"csv_file\" accept=\".csv\" required>`.<br>- Bouton « Lancer la prédiction ».<br>- Zone pour afficher les messages (via Django messages).<br>- Après succès, on peut inclure un petit récapitulatif en utilisant les mêmes fonctions que dans `statistics` mais sur le `validated` DataFrame (on pourrait réutiliser un composant). Pour simplifier, on se contente du téléchargement du CSV ; le récapitulatif pourra être affiché dans une page de résultat si désiré. | - Page accessible, formulaire fonctionne, fichier CSV retourné. |
| 4 | (Optionnel) Afficher un récapitulatif après le téléchargement | - Dans la vue, au lieu de retourner directement le CSV, on pourrait stocker le DataFrame en session, rediriger vers une page `batch_predict_result` qui lit depuis la session et montre les mêmes graphiques que dans `statistics`. Mais pour rester dans le cadre « sans laisser une miette », on ajoute cette étape supplémentaire. | - Créer une vue `batch_predict_result` qui récupère le DataFrame depuis la request.session (ou un cache temporaire).<br>- Réutiliser le code de `statistics` pour générer `charts_data` et `association_factors`.<br>- Afficher les mêmes cartes. | - Après téléchargement, l’utilisateur voit un aperçu avant de quitter. |
| 5 | Tests | `predictor/tests.py` (nouvelle classe `BatchPredictTests`) | - Simuler un POST avec un fichier CSV factice (via `SimpleUploadedFile`).<br>- Vérifier que la réponse est un CSV avec le bon nombre de lignes et les colonnes attendues.<br>- Vérifier les messages de succès/erreur. | - Tests passent. |
| 6 | Documentation README | `README.md` | - Ajouter une sous‑section « Prédiction par lot ». | - README à jour. |

### 2.4 Ordre d’exécution
1. Écrire la vue `batch_predict` + URL.  
2. Créer le template de formulaire.  
3. (Optionnel) Ajouter la vue de résultat et le stockage en session.  
4. Écrire les tests.  
5. Mettre à jour le README.  

### 2.5 Points de vigilance
- La validation du CSV réutilise `validate_training_dataframe` qui nécessite une colonne satisfaction ; on ajoute une colonne factice puis on la retire après.  
- Pour de très gros fichiers, la boucle itérative sur `iterrows()` peut être lente ; on peut vectoriser l’appel à `predict_satisfaction` en passant le entier `DataFrame` au modèle, mais la fonction actuelle accepte une dict. On peut créer une version vectorisée dans `neural_network_model.py` si besoin.  
- Nettoyage des éventuels fichiers temporaires stockés en session (utiliser `request.session.modified = True` et choisir une durée de vie courte).  

---

## 3. Gestion avancée des modèles

### 3.1 Objectifs
- Permettre à l’utilisateur de voir la liste de tous les modèles entraînés, leurs métriques, et d’activer/désactiver un modèle sans ré‑entraîner.  
- Ajouter, dans la page d’entraînement, un tableau récapitulatif avec un bouton « Activer ce modèle ».  
- Offrir une validation croisée (k‑fold) lors de l’entraînement pour obtenir un écart‑type des métriques.  
- Proposer un petit grid‑search sur deux hyper‑paramètres (taille de couches, alpha) pour améliorer automatiquement le modèle.  

### 3.2 Prérequis
- Le modèle `ModelTraining` possède déjà les champs `accuracy`, `dataset_size`, `model_file`, `notes`, `is_active`. Aucun changement de schéma nécessaire.  

### 3.3 Tâches

| # | Tâche | Fichiers | Détails / Code | Validation |
|---|-------|----------|----------------|------------|
| 1 | Modifier la vue `train_model` pour retourner les métriques de validation croisée | `predictor/views.py` | - Après l’entraînement hold‑out, effectuer `cross_val_score` sur l’ensemble des données (avec le même pipeline).<br>- Calculer mean et std pour accuracy, f1, etc.<br>- Ajouter ces valeurs au dictionnaire `metrics` sous des clés `accuracy_cv_mean`, `accuracy_cv_std`, etc.<br>- Passer ces métriques au template. | - Après soumission du formulaire d’entraînement, la page de résultat affiche les nouvelles lignes “CV mean ± std”. |
| 2 | Ajouter un petit grid‑search (2×2) sur hyper‑paramètres du MLP | `predictor/views.py` (fonction interne `train_model_with_gridsearch`) | - Définir une liste de paramètres : `hidden_layer_sizes` = [(64,32), (128,64,32)], `alpha` = [0.0001, 0.001].\n- Boucle : pour chaque combinaison, entraîner un modèle (en réutilisant la même fonction `train_model` mais en passant les paramètres via un arguments supplémentaire).\n- Garder le meilleur modèle selon le F1‑score moyen de la validation croisée.\n- Enregistrer ce meilleur modèle comme actif. | - À la fin de l’entraînement, un message indique les hyper‑paramètres sélectionnés. |
| 3 | Modifier le template `train.html` pour montrer le tableau de tous les modèles | `template/predictor/train.html` | - Récupérer `trainings` déjà présent (liste de tous les ModelTraining).\n- Ajouter un tableau avec colonnes : Date, Accuracy, F1, Taille jeu, Notes, État (Actif/Inactif), Bouton « Activer » (seulement si non actif).\n- Le bouton pointe vers une nouvelle vue `activate_model`. | - Le tableau s’affiche avec toutes les lignes d’entraînements précédents. |
| 4 | Créer la vue `activate_model` | `predictor/views.py` | ```python\n@login_required(login_url='login_register')\n@require_POST\ndef activate_model(request, pk):\n    training = get_object_or_404(ModelTraining, pk=pk)\n    with transaction.atomic():\n        ModelTraining.objects.filter(is_active=True).update(is_active=False)\n        training.is_active = True\n        training.save()\n    notify_user(request.user, 'Modèle activé', f'Modèle #{training.id} est maintenant actif.', level='success', event_type='training', target_url=reverse('train_model'))\n    messages.success(request, f'Modèle #{training.id} activé.')\n    return redirect('train_model')\n``` | - Après POST, le modèle sélectionné devient actif (vérifiable dans la base et dans l’affichage). |
| 5 | Ajouter l’URL correspondante | `predictor/urls.py` | - `path('activate/<int:pk>/', views.activate_model, name='activate_model'),` | - `reverse('activate_model', args=[1])` retourne une URL valide. |
| 6 | Sécuriser : seules les POST autorisées, vérifier que l’utilisateur est connecté (déjà via décorateur). | - | - | |
| 7 | Ajouter un message d’avertissement si aucun modèle n’est actif (dans les vues qui chargent le modèle actif) | `predictor/views.py` (fonction `_active_model_summary`) | - Retourner un dicton avec un champ `"warning": "Aucun modèle actif"` quand `model_data is None and training is None`.<br>- Propager ce warning aux templates (`home`, `statistics`, `predict`). | - Lors d’accès à ces pages sans modèle actif, un bandeau d’avertissement apparaît. |
| 8 | Mettre à jour les templates pour afficher le warning | `template/predictor/base.html` (ou chaque template spécifique) | - Ajouter une boucle `{% if active_model.warning %}<div class=\"alert alert-warning\">{{ active_model.warning }}</div>{% endif %}` dans le `main-content`. | - Le warning apparaît au besoin. |
| 9 | Tests unitaires pour la nouvelles vues | `predictor/tests.py` (nouvelle classe `ModelManagementTests`) | - Créer plusieurs modèles via le gestionnaire, tester l’activation/désactivation, vérifier qu’un seul modèle est actif à la fois.<br>- Vérifier que la vue `train_model` enregistre bien les métriques CV. | - Tous les tests passent. |
|10| Documentation dans README | `README.md` | - Ajouter une section « Gestion avancée des modèles ». | - README à jour. |

### 3.4 Ordre d’exécution
1. Implémentation de la validation croisée + grid‑search dans `views.py`.  
2. Création de la vue `activate_model` + URL.  
3. Mise à jour du tableau dans `train.html`.  
4. Ajout du warning et de son affichage.  
5. Écriture des tests.  
6. Documentation.  

### 3.5 Points de vigilance
- Le grid‑search entraîne plusieurs modèles ; il faut nettoyer les artefacts temporaires ou bien garder uniquement le meilleur. On peut choisir de supprimer les modèles non sélectionnés du répertoire `model_artifacts` après sélection.  
- La validation croisée doit être faite sur le même pipeline que celui utilisé pour l’entraînement final afin d’éviter des différences de prétraitement.  
- Lors de l’activation, s’assurer qu’aucun autre processus n’est en train d’entraîner un modèle (cela est déjà géré par le flag `is_active` mis à jour dans une transaction).  

---

## 4. API REST / intégration externe

### 4.1 Objectifs
- Exposer une API REST sécurisée permettant d’interagir avec l’application depuis des clients externes (applications mobiles, autres services, scripts).  
- Fournir une documentation interactive (OpenAPI/Swagger) pour faciliter l’adoption.  

### 4.2 Prérequis
- Installer `djangorestframework` et `djangorestframework-simplejwt` (ou `drf-spectacular` pour la doc).  
- Configurer l’authentification JWT (ou session) pour protéger les endpoints.  

### 4.3 Tâches

| # | Tâche | Fichiers | Détails / Code | Validation |
|---|-------|----------|----------------|------------|
| 1 | Ajouter dépendances DRF | `requirements.txt` | ```\ndjangorestframework==3.15.0\ndjangorestframework-simplejwt==5.3.0\ndrf-spectacular==0.27.0\n``` | `pip install -r requirements.txt` réussie |
| 2 | Configurer settings.py | `student_satisfaction_project/settings.py` | - Ajouter `'rest_framework'`, `'rest_framework_simplejwt.token_blacklist'` à `INSTALLED_APPS`.\n- Configurer `REST_FRAMEWORK` :\n```python\nREST_FRAMEWORK = {\n    'DEFAULT_AUTHENTICATION_CLASSES': (\n        'rest_framework_simplejwt.authentication.JWTAuthentication',\n    ),\n    'DEFAULT_PERMISSION_CLASSES': (\n        'rest_framework.permissions.IsAuthenticated',\n    ),\n    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',\n}\n```\n- Ajouter les URLs JWT :\n```python\nfrom rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView\nurlpatterns += [\n    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),\n    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),\n]\n``` | - Après `python manage.py check`, aucune erreur.<br>- Les endpoints `/api/token/` et `/api/token/refresh/` répondent. |
| 3 | Créer une application `api` (ou intégrer dans `predictor`) | - `python manage.py startapp api` (optionnel).<br>- Dans `api/serializers.py` définir des sérialiseurs pour `StudentFeedback`, `ModelTraining`.<br>- Dans `api/views.py` définir des `ViewSet` (ou `APIView`) pour les opérations CRUD sur les feedbacks, liste des modèles, activation d’un modèle, prédiction simple. | - Les sérialiseurs sont importables sans erreur.<br>- Les vues retournent les bons statuts HTTP. |
| 4 | Définir les URLs de l’API | `api/urls.py` (ou `predictor/urls.py`) | ```python\nfrom rest_framework.routers import DefaultRouter\nfrom . import views\nrouter = DefaultRouter()\nrouter.register(r'feedbacks', views.FeedbackViewSet, basename='feedback')\nrouter.register(r'trainings', views.ModelTrainingViewSet, basename='training')\nurlpatterns = [\n    path('api/', include(router.urls)),\n    path('api/predict/', views.PredictAPIView.as_view(), name='api-predict'),\n]\n``` | - `reverse('api-predict')` retourne une URL valide. |
| 5 | Implémenter la vue de prédiction API | `api/views.py` (ou `predictor/views.py`) | ```python\nfrom rest_framework.views import APIView\nfrom rest_framework.response import Response\nfrom rest_framework.permissions import IsAuthenticated\nfrom .neural_network_model import load_current_model, predict_satisfaction\n\nclass PredictAPIView(APIView):\n    permission_classes = [IsAuthenticated]\n    def post(self, request):\n        data = request.data\n        required = ['qualite_enseignement', 'charge_travail', 'interactivite', 'type_cours', 'niveau_etudiant']\n        if any(field not in data for field in required):\n            return Response({'error': 'Missing fields'}, status=400)\n        model_data = load_current_model()\n        if model_data is None:\n            return Response({'error': 'No active model'}, status=400)\n        try:\n            result = predict_satisfaction(model_data, data)\n            return Response(result)\n        except Exception as e:\n            return Response({'error': str(e)}, status=400)\n``` | - Envoi d’un POST JSON avec les caractéristiques renvoie une réponse JSON contenant prédiction et probabilité. |
| 6 | Générer la documentation OpenAPI | - Ajouter dans `urls.py` principal :\n```python\nfrom drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView\nurlpatterns += [\n    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),\n    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),\n]\n``` | - Accès à `/api/docs/` affiche l’interface Swagger avec tous les endpoints. |
| 7 | Écrire des tests API | `api/tests.py` (ou `predictor/tests.py`) | - Utiliser `APITestCase` pour tester l’obtention du token, la prédiction, la liste des feedbacks, etc.<br>- Vérifier les codes de statut et la structure des réponses. | - `python manage.py test api` passe. |
| 8 | Documentation README | `README.md` | - Ajouter une section « API REST / intégration externe » détaillant l’authentification JWT, les endpoints principaux et comment consulter la documentation Swagger. | - README à jour. |

### 4.4 Ordre d’exécution
1. Ajouter dépendances DRF et configurer settings.  
2. Créer l’application `api` (ou réutiliser `predictor`) et définir sérialiseurs/vues.  
3. Définir les URLs API et les endpoints JWT.  
4. Implémenter la vue de prédiction API.  
5. Configurer la documentation Swagger.  
6. Écrire les tests API.  
7. Mettre à jour le README.  

### 4.5 Points de vigilance
- La clé secrète JWT doit être stockée en variable d’environnement (ex. : `JWT_SECRET_KEY`) et jamais committée.  
- Limiter le taux de requêtes (rate limiting) si l’API est exposée publiquement (`django-ratelimit` ou `DRF` throttling).  
- Veiller à ne pas exposer des informations sensibles (comme les mots de passe) dans les réponses d’erreur.  

---

## 5. Expérience utilisateur & accessibilité

### 5.1 Objectifs
- Offrir un thème sombre/clair sélectionnable par l’utilisateur.  
- Compléter l’internationalisation (i18n) pour toutes les chaînes visibles, y compris celles en JavaScript.  
- Améliorer l’accessibilité selon les recommandations WCAG 2.1 (contrastes, navigation au clavier, labels ARIA).  
- Ajouter un profil utilisateur avec modification du mot de passe, de l’e‑mail et visualisation de l’activité.  
- Implémenter la réinitialisation de mot de passe via e‑mail.  

### 5.2 Prérequis
- `django.contrib.auth` déjà présent.  
- Pour le thème sombre/clair, utiliser des variables CSS et une classe sur `<body>` (ou un fichier CSS alternatif).  
- Pour l’e‑mail en dev, utiliser la console backend (`EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`).  

### 5.3 Tâches

| # | Tâche | Fichiers | Détails / Code | Validation |
|---|-------|----------|----------------|------------|
| 1 | Activer le middleware de locale (déjà présent dans la section i18n) – s’assurer qu’il est bien placé. | `student_satisfaction_project/settings.py` | Vérifier l’ordre : `SessionMiddleware` → `LocaleMiddleware` → `CommonMiddleware`. | - Aucun warning au démarrage. |
| 2 | Compléter l’extraction et la traduction des chaînes | `locale/` | - Exécuter `makemessages -l fr` et `makemessages -l en` après chaque ajout de chaîne marquée (`{% trans %}` ou `gettext`).<br>- Compléter les fichiers `django.po` pour les deux langues.<br>- Exécuter `compilemessages`. | - Toutes les chaînes visibles apparaissent traduites lorsqu’on change de langue. |
| 3 | Traduire les chaînes JavaScript (toasts, notifications, texte du bouton « Tout lire ») | - Créer un fichier `static/js/i18n.js` qui définit un objet `window.i18n` contenant les chaînes traduites injectées depuis le template via `{{ i18n_variable|json_script:"i18n" }}`.<br>- Dans les templates, ajouter :\n```html\n<script id=\"i18n\" type=\"application/json\">\n    {{\n        \"toast_success\": \"{% trans \"Succès\" %}\",\n        \"toast_error\": \"{% trans \"Erreur\" %}\",\n        \"notification_read_all\": \"{% trans \"Tout lire\" %}\",\n        ...\n    |json_script:\"i18n\"}}\n</script>\n```\n- Modifier le JavaScript existant pour lire `window.i18n[key]` au lieu de chaînes en dur. | - Après changement de langue, les messages dynamiques (toasts, notifications) s’affichent dans la bonne langue. |
| 4 | Implémenter le thème sombre/clair | - Dans `base.html`, ajouter une case à cocher ou un sélecteur dans le header (à côté du sélecteur de langue) :\n```html\n<label class=\"switch\">\n    <input type=\"checkbox\" id=\"theme-toggle\">\n    <span class=\"slider round\"></span>\n</label>\n```\n- En JavaScript, stocker le choix dans `localStorage` et ajouter/retirer la classe `dark` sur `<body>`.\n- Définir les variables CSS dans `:root` et `.dark` pour les couleurs (ex. : `--app-primary`, `--app-bg`, etc.). | - Le thème persiste entre les sessions (via `localStorage`). Le contraste répond aux normes WCAG (vérifiable avec un outil comme axe). |
| 5 | Améliorer l’accessibilité (WCAG) | - Ajouter `aria-label` aux boutons d’icône (cloche de notification, œil de mot de passe).\n- S’assurer que tous les champs de formulaire possèdent un `<label>` associé (via `for` ou enveloppement).\n- Vérifier le contraste des couleurs avec un outil (axe, Lighthouse) – ajuster les variables CSS si nécessaire.\n- Ajouter des liens de saut (« Skip to main content ») en haut de la page. | - Audit automatisé (axe) ne signale aucune erreur de niveau A/AA. |
| 6 | Créer les vues de profil utilisateur | - `views.py` : `profile(request)` affichant les informations de l’utilisateur, nombre de feedbacks, nombre de modèles entraînés, etc.<br>- `urls.py` : `path('profile/', views.profile, name='profile')`.<br>- Template `template/predictor/profile.html` étendant `base.html`. | - La page `/profile/` s’affiche correctement et montre les données de l’utilisateur connecté. |
| 7 | Permettre la modification du mot de passe | - Utiliser les vues intégrées de Django : `PasswordChangeView`, `PasswordChangeDoneView`.<br>- Ajouter les URLs :<br>`path('password_change/', auth_views.PasswordChangeView.as_view(template_name='predictor/password_change_form.html'), name='password_change'),`<br>`path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='predictor/password_change_done.html'), name='password_change_done'),`<br>- Créer les templates correspondants. | - Après soumission du formulaire, le mot de passe est modifié et l’utilisateur reste connecté (ou redirigé vers la page de succès). |
| 8 | Permettre la modification de l’e‑mail | - Créer un formulaire simple (`EmailChangeForm`) qui vérifie que le nouvel e‑mail n’est pas déjà utilisé, enregistre `user.email`.<br>- Vue `email_change(request)` similaire à la modification de mot de passe. | - Après validation, l’e‑mail de l’utilisateur est mis à jour. |
| 9 | Implémenter la réinitialisation de mot de passe | - Configurer les URLs fournies par Django :<br>`path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),`<br>`path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),`<br>`path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),`<br>`path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),`<br>- Créer les templates d’e‑mail (`registration/password_reset_email.html`, etc.) et les templates de page. | - En utilisant le backend console, l’e‑mail de réinitialisation apparaît dans la console du serveur. En prod, configurer un véritable backend SMTP. |
|10| Écrire des tests pour le profil, le changement de mot de passe et la réinitialisation | `predictor/tests.py` (nouvelle classe `UserProfileTests`) | - Tester l’accès au profil nécessite une authentification.<br>- Tester le changement de mot de passe avec bon et mauvais ancien mot de passe.<br>- Tester la vue de réinitialisation (en mockant l’envoi d’e‑mail). | - Tous les tests passent. |
|11| Documentation README | `README.md` | - Ajouter une section « Expérience utilisateur & accessibilité » décrivant le thème sombre/clair, l’i18n complet, les améliorations WCAG, le profil utilisateur et la réinitialisation de mot de passe. | - README à jour. |

### 5.4 Ordre d’exécution
1. Vérifier/compléter le middleware de locale.  
2. Extraire et traduire toutes les chaînes (faire plusieurs cycles `makemessages`/`compilemessages` au fur et à mesure que l’on marque de nouvelles chaînes).  
3. Implémenter la traduction JavaScript.  
4. Ajouter le thème sombre/clair (variables CSS, sélecteur, script de persistance).  
5. Effectuer les améliorations d’accessibilité (labels, contraste, ARIA, saut de contenu).  
6. Créer les vues de profil, modification du mot de passe, modification de l’e‑mail, réinitialisation de mot de passe.  
7. Écrire les tests associés.  
8. Mettre à jour le README.  

### 5.5 Points de vigilance
- Lors de l’ajout de nouvelles chaînes dans les templates ou le code Python, penser à exécuter `makemessages` à nouveau pour les inclure dans les fichiers `.po`.  
- Le thème sombre/clair doit être testé sur différents navigateurs et appareils pour s’assurer que les variables CSS sont bien appliquées.  
- Pour la réinitialisation de mot de passe en production, configurer un véritable serveur SMTP (ex. : SendMail, Mailgun) et définir `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`.  
- Les vues de modification d’e‑mail et de mot de passe doivent être protégées contre les attaques CSRF (déjà géré par Django tant que le template inclut `{% csrf_token %}`).  

---

## 6. DevOps & qualité du code

### 6.1 Objectifs
- Mettre en place un pipeline d’intégration continue (CI) avec GitHub Actions.  
- Imposer un linting et un formatage automatique (Black, isort, Flake8).  
- Augmenter la couverture de tests et la rendre visible dans le README.  
- Ajouter des health‑checks dans les conteneurs Docker.  
- Introduire un versionnement sémantique et un changelog automatisé.  

### 6.2 Prérequis
- Le dépôt est hébergé sur GitHub (ou un autre service compatible avec les actions).  
- Avoir un compte Docker Hub ou un registre privé si l’on veut pousser les images.  

### 6.3 Tâches

| # | Tâche | Fichiers | Détails / Code | Validation |
|---|-------|----------|----------------|------------|
| 1 | Ajouter les dépendances de développement | `requirements-dev.txt` (ou section `[dev]` dans `pyproject.toml`) | ```\nblack==24.3.0\nisort==5.13.2\nflake8==7.0.0\npytest==8.2.0\npytest-django==4.8.0\ncoverage==7.5.0\n``` | `pip install -r requirements-dev.txt` réussie |
| 2 | Configurer Black et isort | - Créer un fichier `pyproject.toml` à la racine avec les sections :\n```toml\n[tool.black]\nline-length = 100\ntarget-version = ['py312']\n\n[tool.isort]\nprofile = \"black\"\n``` | - L’exécution de `black .` et `isort .` ne modifie aucun fichier (ou les formate selon les règles). |
| 3 | Configurer Flake8 | - Créer un fichier `.flake8` :\n```\n[flake8]\nmax-line-length = 100\nextend-ignore = E203, W503\nexclude = .git,__pycache__,migrations,venv,build,dist\n``` | - `flake8 .` retourne aucune erreur (ou seulement des warnings acceptables). |
| 4 | Créer un script de vérification pré‑commit (optionnel) | - Ajouter un hook `pre-commit` (via le package `pre-commit`) qui exécute `black`, `isort`, `flake8` et les tests. | - Lors d’un `git commit`, le hook bloque le commit si les vérifications échouent. |
| 5 | Mettre en place GitHub Actions | - Créer `.github/workflows/ci.yml` :\n```yaml\nname: CI\n\non:\n  push:\n    branches: [ main, master ]\n  pull_request:\n    branches: [ main, master ]\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    services:\n      postgres:\n        image: postgres:15\n        env:\n          POSTGRES_USER: postgres\n          POSTGRES_PASSWORD: postgres\n          POSTGRES_DB: student_satisfaction\n        ports: [5432:5432]\n        options: >-  --health-cmd \"pg_isready -U postgres\"\n          --health-interval 10s\n          --health-timeout 5s\n          --health-retries 5\n    env:\n      DEBUG: False\n      SECRET_KEY: github-secret-key-for-ci\n      DATABASE_URL: postgres://postgres:postgres@localhost:5432/student_satisfaction\n    steps:\n      - uses: actions/checkout@v4\n      - name: Set up Python\n        uses: actions/setup-python@v5\n        with:\n          python-version: '3.12'\n      - name: Install dependencies\n        run: |\n          python -m pip install --upgrade pip\n          pip install -r requirements.txt\n          pip install -r requirements-dev.txt\n      - name: Lint with flake8\n        run: flake8 predictor\n      - name: Format check with black\n        run: black --check .\n      - name: Import check with isort\n        run: isort --check-only .\n      - name: Run migrations\n        run: python manage.py migrate\n      - name: Run tests\n        run: |\n          coverage run --source='.' manage.py test\n          coverage report\n          cobertura-xml\n      - name: Upload coverage to Codecov\n        uses: codecov/codecov-action@v4\n        with:\n          files: cobertura.xml\n          fail_ci_if_error: true\n``` | - Le workflow s’exécute sur chaque push/PR et indique succès ou échec. |
| 6 | Augmenter la couverture de tests | - Écrire des tests supplémentaires pour les nouvelles fonctionnalités (API, i18n, thèmes, etc.).<br>- Viser une couverture globale ≥ 80 % (ou plus selon les objectifs). | - Après chaque run, `coverage report` montre le pourcentage; le badge peut être ajouté au README. |
| 7 | Ajouter un badge de couverture au README | `README.md` | - Insérer un badge provenant de shields.io ou de Codecov :\n```markdown\n![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/<user>/<gist-id>/raw/coverage.json)\n``` | - Le badge apparaît dans le README et reflète la couverture actuelle. |
| 8 | Ajouter des health‑checks dans le Docker Compose | - Dans `docker-compose.yml`, sous le service `web` :\n```yaml\n    healthcheck:\n      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8000/health/\"]\n      interval: 30s\n      timeout: 10s\n      retries: 3\n```\n- Créer une vue simple `health(request)` qui renvoie `HttpResponse(\"OK\")` et l’URL correspondante. | - `docker compose ps` montre le status `healthy` lorsqu’ l’application répond. |
| 9 | Versionnement sémantique et changelog | - Créer un fichier `CHANGELOG.md` au format Keep a Changelog.<br>- À chaque release, ajouter une nouvelle section conçue avec les types `Added`, `Changed`, `Fixed`, `Removed`.<br>- Utiliser un outil comme `standard-version` ou faire manuellement. | - Le changelog est à jour et suit la convention. |
|10| Documentation README | `README.md` | - Ajouter une section « DevOps & qualité du code » détaillant le CI, le linting, la couverture de tests, les health‑checks Docker et le versionnement sémantique. | - README à jour. |

### 6.4 Ordre d’exécution
1. Ajouter les dépendances de développement et configurer les outils de formatage.  
2. Créer les fichiers de configuration (`pyproject.toml`, `.flake8`).  
3. Mettre en place le workflow GitHub Actions.  
4. Augmenter la couverture de tests en écrivant les tests manquants.  
5. Ajouter le badge de couverture au README.  
6. Configurer les health‑checks dans le Docker Compose et créer la vue `/health/`.  
7. Instaurer le versionnement sémantique et le changelog.  
8. Documenter le tout dans le README.  

### 6.5 Points de vigilance
- Le workflow CI utilise une base de données PostgreSQL en tant que service ; penser à nettoyer les bases entre les runs (les containers sont éphémères).  
- Lors de l’ajout de nouvelles dépendances, pensez à les ajouter aussi dans `requirements-dev.txt` si elles sont uniquement utilisées en développement/test.  
- Les health‑checks doivent être légers afin de ne pas impacter les performances de l’application.  
- Le versionnement sémantique doit être respecté : toute modification rétrocompatible augmente le mineur, toute rupture augmente le majeur, les correctifs augmentent le patch.  

---

## 7. Fonctionnalités pédagogiques / communautaires

### 7.1 Objectifs
- Fournir des explications textuelles automatiques accompagnant les visualisations SHAP.  
- Créer un espace de commentaires/forum rattaché à chaque prédiction (ou à chaque jeu de données) pour permettre aux utilisateurs d’échanger leurs impressions.  
- Mettre en place un système de badges/gamification pour encourager l’utilisation régulière (ex. : « 10 prédictions effectuées », « Modèle avec > 90 % d’accuracy »).  
- Offrir un espace de partage de jeux de données synthétiques générés par le script `generate_synthetic_data.py`.  

### 7.2 Prérequis
- Les modèles et les vues existants sont prêts à recevoir des données complémentaires (nouveaux modèles liés aux commentaires, aux badges, aux jeux de données).  
- L’application utilise déjà le système de messages Django pour les notifications ; on peut réutiliser ce mécanisme pour les alertes de badges.  

### 7.3 Tâches

| # | Tâche | Fichiers | Détails / Code | Validation |
|---|-------|----------|----------------|------------|
| 1 | Créer le modèle `FeedbackComment` | `predictor/models.py` | ```python\nclass FeedbackComment(models.Model):\n    feedback = models.ForeignKey(StudentFeedback, on_delete=models.CASCADE, related_name='comments')\n    author = models.ForeignKey(User, on_delete=models.CASCADE)\n    content = models.TextField()\n    created_at = models.DateTimeField(auto_now_add=True)\n    updated_at = models.DateTimeField(auto_now=True)\n\n    class Meta:\n        ordering = ['-created_at']\n\n    def __str__(self):\n        return f\"Commentaire par {self.author.username} sur avis #{self.feedback_id}\"\n``` | - Après `python manage.py makemigrations` et `migrate`, la table est créée. |
| 2 | Créer le formulaire associé | `predictor/forms.py` | ```python\nclass FeedbackCommentForm(forms.ModelForm):\n    class Meta:\n        model = FeedbackComment\n        fields = ['content']\n        widgets = {\n            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Écrire un commentaire…'})\n        }\n``` | - Le formulaire est importable et rendable dans un template. |
| 3 | Ajouter la vue pour afficher et créer des commentaires | `predictor/views.py` | - Nouvelle vue `feedback_comments(request, pk)` :<br>  * GET : récupérer les commentaires liés au feedback `pk`, les paginer, rendre un template `predictor/feedback_comments.html`.<br>  * POST : traiter le formulaire, créer le commentaire associée à l’utilisateur connecté, envoyer une notification à l’auteur du feedback (optionnel).<br>- Ajouter l’URL : `path('feedback/<int:pk>/comments/', views.feedback_comments, name='feedback_comments')`. | - La page `/feedback/<id>/comments/` liste les commentaires et permet d’en ajouter de nouveaux. |
| 4 | Créer le template des commentaires | `template/predictor/feedback_comments.html` | - Étendre `base.html`.<br>- Afficher la liste des commentaires avec avatar (ou initiale du nom), date, contenu.<br>- Formulaire en bas pour ajouter un nouveau commentaire.<br>- Utiliser les messages Django pour afficher les erreurs/succès. | - Le rendu est propre, responsive (utilise les classes Bootstrap déjà présentes). |
| 5 | Créer le modèle `UserBadge` et les règles d’attribution | `predictor/models.py` | ```python\nclass UserBadge(models.Model):\n    user = models.ForeignKey(User, on_delete=models.CASCADE)\n    badge_slug = models.SlugField(unique=True)  # ex. 'first_prediction', 'model_90_acc'\n    awarded_at = models.DateTimeField(auto_now_add=True)\n\n    class Meta:\n        unique_together = ('user', 'badge_slug')\n\n    def __str__(self):\n        return f\"{self.user.username} – {self.badge_slug}\"\n```\n- Créer un gestionnaire `BadgeManager` (ou des signaux) qui attribue les badges lorsqu certaines conditions sont remplies :<br>  * Après chaque prédiction, inciter un compteur et attribuer \"first_prediction\" si c’est la première.\n>  * Après chaque entraînement, vérifier l’accuracy du modèle ; si ≥ 0.90, attribuer \"model_90_acc\" à l’utilisateur qui a lancé l’entraînement.\n>  * Après chaque lot de prédictions, attribuer \"batch_user\" si ≥ 100 lignes traitées.\n- Utiliser `django.db.models.signals.post_save` sur `StudentFeedback` et `ModelTraining`. | - Après avoir effectué les actions correspondantes, un nouvel enregistrement apparaît dans `UserBadge`. |
| 6 | Créer la vue de affichage des badges (profil) | `predictor/views.py` | - Étendre la vue `profile` pour inclure la liste des badges de l’utilisateur (`UserBadge.objects.filter(user=request.user)`).<br>- Passer cette liste au template du profil. | - Dans la page de profil, on voit une section « Badges » avec les icônes/noms attribués. |
| 7 | Ajouter l’affichage des badges dans le template du profil | `template/predictor/profile.html` | - Ajouter une carte présentant les badges sous forme de petites icônes avecTooltip (texte du badge). | - Les badges apparaissent visuellement dans le profil. |
| 8 | Créer le modèle `SharedDataset` pour partager des jeux de données synthétiques | `predictor/models.py` | ```python\nclass SharedDataset(models.Model):\n    uploader = models.ForeignKey(User, on_delete=models.CASCADE)\n    title = models.CharField(max_length=200)\n    description = models.TextField(blank=True)\n    file = models.FileField(upload_to='shared_datasets/')\n    uploaded_at = models.DateTimeField(auto_now_add=True)\n    is_public = models.BooleanField(default=True)\n\n    def __str__(self):\n        return self.title\n```\n- Créer le formulaire associé (`SharedDatasetForm`) avec validation du type CSV et de la taille maximale. | - Après `migrate`, la table est prête à recevoir des fichiers. |
| 9 | Créer les vues pour lister, télécharger et uploader des jeux de données partagés | `predictor/views.py` | - `shared_datasets_list(request)` : liste paginée des jeux publics (ou privés si l’utilisateur est l’uploader).<br>- `shared_dataset_upload(request)` : formulaire d’upload, sauvegarde le fichier, crée l’enregistrement, notifie les utilisateurs (optionnel).<br>- `shared_dataset_download(request, pk)` : renvoie le fichier avec `Content-Disposition: attachment`.<br>- Ajouter les URLs correspondantes dans `urls.py`. | - Les pages permettent d’uploader un CSV, de le voir dans la liste et de le télécharger. |
| 10 | Créer les templates associés | `template/predictor/shared_datasets_list.html`, `template/predictor/shared_dataset_upload.html` | - Réutiliser le layout de base, afficher les cartes avec titre, description, date, bouton de téléchargement.<br>- Le formulaire d’upload utilise les classes Bootstrap. | - Les pages sont fonctionnelles et responsives. |
| 11 | Générer des explications textuelles automatiques à partir des valeurs SHAP | `predictor/utils_explain.py` | - Ajouter une fonction `shap_to_text(explanation_dict)` qui construit une phrase comme :\n```text\nLa prédiction est principalement influencée par {feature_1} ({contribution_1:+.2f}) et {feature_2} ({contribution_2:+.2f}), tandis que {feature_3} a un effet faible ({contribution_3:+.2f}).\n```\n- Trier les caractéristiques par valeur absolue décroissante, prendre les deux ou trois premières. | - La fonction retourne une chaîne lisible en français (ou en fonction de la langue active via `gettext`). |
| 12 | Intégrer l’explication textuelle dans la vue de prédiction | `predictor/views.py` | - Après avoir obtenu `explanation` (dict SHAP), appeler `text_explanation = shap_to_text(explanation)` et l’ajouter au contexte sous `"text_explanation"`.<br>- Passer également la traduction si nécessaire (la fonction utilise déjà `gettext`). | - La variable `text_explanation` apparaît dans le contexte après soumission du formulaire. |
| 13 | Afficher l’explication textuelle dans le template `predict.html` | `template/predictor/predict.html` | - Sous le bloc d’explication SHAP, ajouter :\n```html\n{% if text_explanation %}\n<div class=\"alert alert-info mt-3\">\n    {{ text_explanation }}\n</div>\n{% endif %}\n``` | - L’explication textuelle apparaît en français (ou anglais selon la langue sélectionnée). |
| 14 | Écrire des tests pour les nouvelles fonctionnalités communautaires | `predictor/tests.py` (nouvelle classe `CommunityFeaturesTests`) | - Tester la création d’un commentaire, la liste des commentaires, la pagination.<br>- Tester l’attribution automatique des badges via les signaux.<br>- Tester l’upload et le téléchargement d’un jeu de données partagé.<br>- Tester la fonction `shap_to_text` avec différents entrés. | - Tous les tests passent. |
| 15 | Documentation README | `README.md` | - Ajouter une section « Fonctionnalités pédagogiques / communautaires » détaillant les commentaires, les badges/gamification, le partage de jeux de données synthétiques et les explications textuelles automatiques. | - README à jour. |

### 7.4 Ordre d’exécution
1. Créer les modèles (`FeedbackComment`, `UserBadge`, `SharedDataset`) et générer les migrations.  
2. Créer les formulaires associés.  
3. Implémenter les vues et les URLs pour les commentaires, les badges (via les signaux), les jeux de données partagés.  
4. Créer les templates correspondants.  
5. Ajouter la fonction d’explication textuelle SHAP et l’intégrer dans la vue de prédiction.  
6. Écrire les tests unitaires pour chaque nouvelle fonctionnalité.  
7. Mettre à jour le README avec la documentation complète.  

### 7.5 Points de vigilance
- Les signaux doivent être déconnectés lors des tests afin d’éviter des effets de bord inattendus. Utiliser le décorateur `@override_settings` ou `disconnect` dans le `setUp` des tests.  
- La gestion des fichiers uploadés (jeux de données partagés) doit prendre en compte la sécurité : vérifier l’extension, limiter la taille, stocker en dehors du répertoire racine du projet si possible (utiliser `MEDIA_ROOT`).  
- Les explications textuelles doivent être traduites ; la fonction `shap_to_text` doit utiliser `gettext` pour chaque morceau de phrase afin de respecter la langue active.  
- Le système de badges doit être idempotent : un même badge ne peut être attribué qu’une seule fois à un utilisateur (contrainte `unique_together` dans le modèle).  
- Lors de l’affichage des listes de commentaires ou de jeux de données, penser à la pagination pour éviter des pages trop lourdes.  

---

## Plan global d’implémentation (ordre recommandé)

| Phase | Axe principal | Étapes clés |
|-------|---------------|-------------|
| **0** | Préparation | - Sauvegarder l’état actuel (branche git).<br>- Créer une branche `feature/ameliorations-complete`. |
| **1** | Docker & settings (DevOps) | - Étape 6 (Dockerfile, compose, settings, CI, linting, tests, health‑check, versionning).<br>- Vérifier que l’app fonctionne en dev via Docker. |
| **2** | Internationalisation (i18n) | - Étape 5 (settings, locales, traduction complète, sélecteur de langue, traduction JS).<br>- Valider le bascule FR/EN sur les pages principales. |
| **3** | Interprétabilité des prédictions | - Étape 1 (utils_explain, importance globale, explication locale, texte SHAP, templates, tests). |
| **4** | Prédiction par lot | - Étape 2 (vue batch_predict, template, résultat éventuel, tests). |
| **5** | Gestion avancée des modèles | - Étape 3 (validation croisée, grid‑search, activation modèle, tableau, warning, tests). |
| **6** | API REST / intégration externe | - Étape 4 (DRF, JWT, vues API, documentation Swagger, tests). |
| **7** | Expérience utilisateur & accessibilité | - Étape 5 (thème sombre/clair, accessibilité WCAG, profil, changement de mot de passe/e‑mail, réinitialisation, tests). |
| **8** | Fonctionnalités pédagogiques / communautaires | - Étape 7 (modèles commentaires, badges, jeux de données partagés, explication textuelle SHAP, templates, tests). |
| **9** | Documentation finale | - Mettre à jour `README.md` avec toutes les nouvelles sections.<br>- Réviser le `.gitignore`.<br>- Faire un `git push` et ouvrir une pull‑request pour revue. |
|**10**| Nettoyage & récupération | - Supprimer les branches temporaires si besoin, merger vers `main`. |

Chaque phase doit être accompagnée d’un commit décrivant les changements, et l’exécution de la suite de tests (`python manage.py test`) doit passer avant de passer à la phase suivante.

---

## Résumé des livrables (fichiers à créer / modifier)

| Type | Chemin | Description |
|------|--------|-------------|
| **Code** | `predictor/utils_explain.py` | Utilitaires d’explication globale, SHAP locaux et texte explicatif. |
| **Code** | `predictor/views.py` | Ajout des nouvelles fonctions (global importance, expliquer prédiction, texte SHAP, activation modèle, batch predict, validation croisée, grid‑search, API, commentaires, badges, jeux de données partagés, santé, profil, etc.). |
| **Code** | `predictor/urls.py` | Nouveaux chemins (`activate/<int:pk>/`, `batch-predict/`, `feedback/<int:pk>/comments/`, `shared-datasets/`, `api/`, etc.). |
| **Code** | `api/…` (ou dans `predictor`) | Serialiseurs, vues et URLs pour l’API REST (DJRF + JWT). |
| **Templates** | `template/predictor/statistics.html` | Affichage importance globale. |
| **Templates** | `template/predictor/predict.html` | Affichation explication SHAP + texte explicatif. |
| **Templates** | `template/predictor/train.html` | Tableau des modèles + bouton d’activation. |
| **Templates** | `template/predictor/batch_predict.html` | Formulaire d’upload CSV lot. |
| **Templates** | `template/predictor/feedback_comments.html` | Liste et formulaire de commentaires. |
| **Templates** | `template/predictor/profile.html` | Profil utilisateur avec badges. |
| **Templates** | `template/predictor/shared_datasets_list.html` / `shared_dataset_upload.html` | Listage et upload de jeux de données partagés. |
| **Templates** | `template/base.html` | Sélecteur de langue, thème sombre/clair, zone de warning, liens de saut. |
| **Static** | `static/js/i18n.js` (ou similaire) | Injection des chaînes traduites pour le JavaScript (toasts, notifications). |
| **Tests** | `predictor/tests.py` | Nouvelles classes de tests : `ExplanationTests`, `ModelManagementTests`, `BatchPredictTests`, `APITests` (ou `api/tests.py`), `UserProfileTests`, `CommunityFeaturesTests`, éventuellement `I18nTests`. |
| **Configuration** | `requirements.txt` | Ajout de `shap==0.45.1`, `djangorestframework`, `djangorestframework-simplejwt`, `drf-spectacular`. |
| **Configuration** | `requirements-dev.txt` | `black`, `isort`, `flake8`, `pytest`, `pytest-django`, `coverage`. |
| **Configuration** | `student_satisfaction_project/settings.py` | MIDDLEWARE, LANGUAGE_CODE, LOCALE_PATHS, configuration DRF/JWT, variables d’environnement pour DB, secrets. |
| **Configuration** | `locale/en/LC_MESSAGES/django.po` + `.mo` | Traduction anglaise. |
| **Configuration** | `Dockerfile` | Image Docker. |
| **Configuration** | `.dockerignore` | Fichiers à exclure de l’image. |
| **Configuration** | `docker-compose.yml` | Orchestration développement (web + db). |
| **Configuration** | `docker-compose.prod.yml` (optionnel) | Orchestration production. |
| **Configuration** | `.github/workflows/ci.yml` | Pipeline GitHub Actions (CI). |
| **Configuration** | `CHANGELOG.md` | Journal des modifications suivant Keep a Changelog. |
| **Documentation** | `README.md` | Sections détaillant toutes les nouvelles fonctionnalités. |
| **Documentation** | `.env.dev` / `.env.prod` (exemple) | Variables d’environnement pour dev / prod. |

---

### Conclusion

En suivant ce plan, le projet **Student Satisfaction Project** sera enrichi de façon exhaustive :

- **Transparence** grâce à l’interprétabilité des prédictions (importance globale + explication SHAP locale + texte explicatif).  
- **Flexibilité** de gestion des modèles (activation/désactivation, comparaison, validation croisée, réglage d’hyperparamètres).  
- **Capacité d’analyse de masse** (prédiction par lot avec récapitulatif intégré).  
- **Interopérabilité** via une API REST sécurisée, documentée avec Swagger.  
- **Expérience utilisateur optimisée** (thème sombre/clair, i18n complet, conformité WCAG, profil utilisateur, réinitialisation de mot de passe).  
- **Qualité et livraison automatisées** (CI GitHub Actions, linting/formatage, couverture de tests, health‑checks Docker, versionnement sémantique).  
- **Valeur pédagogique et communautaire** (explications textuelles automatiques, espace de commentaires, badges/gamification, partage de jeux de données synthétiques).  

Chaque axe est présenté avec un niveau de détail permettant de passer directement à l’implémentation, en s’appuyant sur des tests automatisés pour garantir l’absence de régressions et une documentation claire pour les utilisateurs et les administrateurs.  

Vous pouvez maintenant copier le contenu ci‑dessus dans le fichier **`plan_ameliorations.md`** à la racine du dépôt et commencer l’implémentation conformément aux étapes détaillées. Bonne continuation !  

---