# Changelog

Les changements notables du projet sont regroupés dans ce fichier.

## [Unreleased]

### Added

- adaptation Vercel Django zéro-configuration avec Python 3.12 ;
- intégration Neon serverless avec connexion poolée et URL directe pour les migrations ;
- hosts et origines CSRF dérivés des variables système Vercel sans wildcard ;
- build Vercel idempotent pour migrations, RBAC et bootstrap portfolio ;
- validation CI de la cible de production sous Python 3.12 ;
- configuration production fail-closed avec PostgreSQL configurable ;
- Gunicorn, WhiteNoise et health-check `/health/` ;
- `.env.example` sans secrets réels ;
- modèle ML Pipeline v3 packagé pour un déploiement neuf ;
- compte public portfolio protégé et limité à la prédiction ;
- bootstrap idempotent du modèle et du compte portfolio ;
- CI GitHub Actions avec tests SQLite et smoke test PostgreSQL ;
- vérification SHA-256 reproductible de l'artefact ML ;
- documentation de déploiement production.

### Security

- `DEBUG=True` refusé en environnement production ;
- secret Django, hosts, origines CSRF et PostgreSQL obligatoires en production ;
- compte portfolio non administrateur et non modifiable par l'interface métier ;
- prédictions du compte partagé exclues des statistiques persistées ;
- actions GitHub tierces épinglées à des SHA complets.

## [1.2.0-rc1] - 2026-08-19

### Added

- navigation responsive V16 ;
- drawer mobile et bottom navigation ;
- navigation partielle sans rechargement visuel complet ;
- sélecteurs de langue et thème stabilisés ;
- cartes métriques mobiles responsive.

### Validation

- 341 tests Django validés avant le gel V16.

## [1.1.0]

- consolidation i18n ;
- RBAC fail-closed ;
- interface bilingue et contrôle d'accès métier.
