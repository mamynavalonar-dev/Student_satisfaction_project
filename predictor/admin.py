# predictor/admin.py
# Importation des modules nécessaires de Django pour l'administration
from django.contrib import admin
# Importation des modèles définis dans models.py
from .models import StudentFeedback, ModelTraining, Notification

# Enregistrement du modèle StudentFeedback dans l'admin avec une configuration personnalisée
@admin.register(StudentFeedback)
class StudentFeedbackAdmin(admin.ModelAdmin):
    # list_display : colonnes qui s'affichent dans la liste principale du modèle
    list_display = [
        'id',                      # Identifiant unique de l'entrée
        'qualite_enseignement',    # Note de qualité de l'enseignement
        'charge_travail',          # Charge de travail perçue
        'interactivite',           # Niveau d'interactivité
        'type_cours',              # Type du cours (présentiel/distanciel)
        'niveau_etudiant',         # Niveau de l'étudiant (L1, L2, ...)
        'predicted_satisfaction',  # Satisfaction prédite par le modèle (CORRIGÉ)
        'probability_satisfied',   # Probabilité calculée pour être satisfait
        'created_at'               # Date de création de l'entrée
    ]
    
    # list_filter : permet de filtrer facilement les entrées dans l'admin
    list_filter = [
        'type_cours', 
        'niveau_etudiant', 
        'predicted_satisfaction',  # CORRIGÉ
        'created_at'
    ]
    
    # search_fields : permet de rechercher rapidement dans certaines colonnes
    search_fields = ['id', 'type_cours', 'niveau_etudiant']
    
    # readonly_fields : champs qui ne peuvent pas être modifiés depuis l'admin
    readonly_fields = ['created_at', 'updated_at']
    
    # ordering : définit l'ordre d'affichage par défaut (ici du plus récent au plus ancien)
    ordering = ['-created_at']
    
    # fieldsets : permet de regrouper les champs dans des sections lisibles
    fieldsets = (
        ('Caractéristiques du Cours', {   # Section 1 : caractéristiques du cours
            'fields': (
                'qualite_enseignement',
                'charge_travail',
                'interactivite',
                'type_cours',
                'niveau_etudiant'
            )
        }),
        ('Résultat de la Prédiction', {    # Section 2 : satisfaction prédite (TITRE ET CHAMPS CORRIGÉS)
            'fields': (
                'predicted_satisfaction',
                'probability_satisfied'
            )
        }),
        ('Métadonnées', {                  # Section 3 : informations système
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)       # rend la section repliable
        })
    )


# Enregistrement du modèle ModelTraining dans l'admin avec configuration personnalisée
@admin.register(ModelTraining)
class ModelTrainingAdmin(admin.ModelAdmin):
    # Colonnes affichées dans la liste principale
    list_display = [
        'id',               # Identifiant unique
        'training_date',    # Date d'entraînement du modèle
        'accuracy',         # Précision obtenue sur les données de test
        'dataset_size',     # Taille du jeu de données utilisé pour l'entraînement
        'is_active',        # Indique si ce modèle est actuellement utilisé
        'model_file'        # Nom du fichier du modèle sauvegardé
    ]
    
    # Colonnes sur lesquelles on peut filtrer
    list_filter = [
        'is_active',
        'training_date'
    ]
    
    # Colonnes sur lesquelles on peut rechercher
    search_fields = ['model_file', 'notes']
    
    # Champs en lecture seule
    readonly_fields = ['training_date']
    
    # Ordre d'affichage : du plus récent au plus ancien
    ordering = ['-training_date']
    
    # Regroupement des champs dans des sections lisibles
    fieldsets = (
        ('Information du Modèle', {   # Section principale : infos essentielles
            'fields': (
                'model_file',
                'accuracy',
                'dataset_size',
                'is_active'
            )
        }),
        ('Détails', {                  # Section secondaire : détails supplémentaires
            'fields': (
                'notes',
                'training_date'
            )
        })
    )
    
    # Permet de personnaliser la requête utilisée pour récupérer les objets
    # Ici, on utilise juste la requête par défaut de Django
    def get_queryset(self, request):
        return super().get_queryset(request)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "title", "level", "event_type", "is_read", "created_at"]
    list_filter = ["level", "event_type", "is_read", "created_at"]
    search_fields = ["user__username", "title", "message"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]

