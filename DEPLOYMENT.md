# Déploiement production — Student Satisfaction Project

Ce document décrit la procédure de déploiement de la branche V17 sans dépendre d'un hébergeur particulier. Le service choisi doit fournir Python 3.11+, HTTPS, des variables d'environnement et PostgreSQL.

## 1. Pré-requis du service

Le déploiement doit disposer de :

- Python 3.11 ou version compatible avec `requirements.txt` ;
- PostgreSQL persistant ;
- HTTPS ;
- variables d'environnement/secrets ;
- un processus web long-running ;
- une commande de build et, idéalement, une commande pre-deploy/release.

Le fichier `Procfile` contient la commande Gunicorn du projet.

## 2. Variables d'environnement obligatoires

Copier la structure de `.env.example` dans le gestionnaire de variables de la plateforme. Ne pas téléverser de fichier `.env` contenant de vraies valeurs.

Production minimale :

```text
DJANGO_ENV=production
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<secret Django long et aléatoire>
DJANGO_ALLOWED_HOSTS=<domaine fourni par l'hébergeur>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<domaine fourni par l'hébergeur>
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>

DJANGO_SECURE_SSL_REDIRECT=1
DJANGO_TRUST_X_FORWARDED_PROTO=<0 ou 1 selon le proxy de l'hébergeur>
DJANGO_HSTS_SECONDS=3600
DJANGO_HSTS_INCLUDE_SUBDOMAINS=0
DJANGO_HSTS_PRELOAD=0

PORTFOLIO_DEMO_ENABLED=1
PORTFOLIO_DEMO_USERNAME=portfolio-demo
PORTFOLIO_DEMO_EMAIL=portfolio-demo@example.invalid
PORTFOLIO_DEMO_PASSWORD=<mot de passe public de démonstration, 12 caractères minimum>
PORTFOLIO_MODEL_PATH=deployment/model/portfolio_model.joblib
```

`DJANGO_TRUST_X_FORWARDED_PROTO=1` ne doit être utilisé que si le proxy de la plateforme contrôle correctement `X-Forwarded-Proto`.

Ne pas activer `DJANGO_HSTS_INCLUDE_SUBDOMAINS=1` ou `DJANGO_HSTS_PRELOAD=1` avant d'avoir confirmé que le domaine et tous ses sous-domaines resteront exclusivement en HTTPS.

## 3. E-mail / réinitialisation de mot de passe

Le backend console convient uniquement au développement. Pour une vraie réinitialisation de mot de passe, configurer un SMTP :

```text
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=<adresse d'expédition>
SERVER_EMAIL=<adresse serveur>
EMAIL_HOST=<serveur SMTP>
EMAIL_PORT=587
EMAIL_HOST_USER=<utilisateur SMTP>
EMAIL_HOST_PASSWORD=<secret SMTP>
EMAIL_USE_TLS=1
EMAIL_USE_SSL=0
EMAIL_TIMEOUT=10
```

Ne jamais publier les identifiants SMTP dans Git.

## 4. Vérification de l'artefact ML

Avant toute release :

```powershell
python .\scripts\verify_release.py
```

Le fichier `deployment/model/portfolio_model.sha256` est la source de vérité du hash du modèle packagé. La vérification doit afficher `RELEASE_CHECK_OK`.

Le modèle portfolio est versionné avec le code afin qu'un déploiement neuf puisse effectuer des prédictions immédiatement après le bootstrap.

## 5. Build

Commande générique de build :

```text
python -m pip install -r requirements.txt
python manage.py collectstatic --noinput
```

Certaines plateformes installent automatiquement `requirements.txt`. Dans ce cas, conserver au minimum `python manage.py collectstatic --noinput` comme étape de build.

## 6. Base de données et bootstrap

Après création de PostgreSQL et avant l'ouverture du service :

```text
python manage.py migrate --noinput
python manage.py setup_roles
python manage.py bootstrap_portfolio
```

`bootstrap_portfolio` est idempotente : elle crée ou remet en conformité le compte public et le modèle actif packagé.

Elle ne doit pas être remplacée par un entraînement automatique à chaque déploiement.

## 7. Compte administrateur personnel

Le compte public portfolio ne doit jamais devenir administrateur.

Pour créer votre compte d'administration personnel :

```text
python manage.py createsuperuser
python manage.py setup_roles --promote-superuser <nom_utilisateur>
```

Conserver ces identifiants privés.

## 8. Processus web

Commande de démarrage équivalente au `Procfile` :

```text
gunicorn student_satisfaction_project.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile -
```

La plateforme doit fournir `PORT` lorsqu'elle l'impose.

## 9. Health-check

Configurer le health-check HTTP de la plateforme sur :

```text
/health/
```

Réponse attendue avec une base accessible :

```json
{"status":"ok"}
```

Une base indisponible renvoie HTTP 503 sans exposer les détails de connexion.

## 10. Vérifications après déploiement

Vérifier dans cet ordre :

```text
1. /health/ retourne HTTP 200.
2. Les fichiers CSS/JS se chargent sans 404.
3. Le compte administrateur personnel peut se connecter.
4. Le compte portfolio peut se connecter.
5. Une prédiction portfolio réelle fonctionne.
6. Cette prédiction n'apparaît pas dans StudentFeedback/statistiques.
7. Le compte portfolio ne peut pas modifier son profil, son mot de passe ou son rôle.
8. L'administration, l'entraînement, les données et les statistiques restent interdits au compte portfolio.
9. Le changement FR/EN et le thème fonctionnent sur desktop et mobile.
10. La réinitialisation de mot de passe envoie réellement un e-mail lorsque SMTP est configuré.
```

## 11. Identifiants publics dans le portfolio

Le nom d'utilisateur et le mot de passe du compte de démonstration peuvent être affichés dans le portfolio puisqu'il s'agit volontairement d'un compte public limité.

Ne jamais afficher :

- le mot de passe du superutilisateur ;
- `DJANGO_SECRET_KEY` ;
- `DATABASE_URL` ;
- les secrets SMTP ;
- des tokens JWT d'administration.

Pour changer le mot de passe public, modifier `PORTFOLIO_DEMO_PASSWORD` dans la plateforme puis relancer :

```text
python manage.py bootstrap_portfolio
```

## 12. Release Git

Avant fusion vers `main` :

```powershell
python .\scripts\verify_release.py
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
git diff --check
git status --short
```

Après validation de GitHub Actions, fusionner la branche de production vers `main`, taguer la release puis pousser le tag.

Le choix exact de l'hébergeur et ses commandes spécifiques seront ajoutés seulement après sélection de la plateforme.
