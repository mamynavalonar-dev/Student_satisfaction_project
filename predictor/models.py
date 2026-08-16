# predictor/models.py
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

class StudentFeedback(models.Model):
    TYPE_COURS_CHOICES = [
        ('présentiel', 'Présentiel'),
        ('distanciel', 'Distanciel'),
        ('hybride', 'Hybride'),
    ]
    
    NIVEAU_CHOICES = [
        ('L1', 'L1'),
        ('L2', 'L2'),
        ('L3', 'L3'),
        ('M1', 'M1'),
        ('M2', 'M2'),
    ]
    
    qualite_enseignement = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(7)]
    )
    charge_travail = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(7)]
    )
    interactivite = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(7)]
    )
    type_cours = models.CharField(max_length=20, choices=TYPE_COURS_CHOICES)
    niveau_etudiant = models.CharField(max_length=10, choices=NIVEAU_CHOICES)
    
    # Résultats de prédiction
    predicted_satisfaction = models.BooleanField(null=True, blank=True)
    probability_satisfied = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Avis #{self.id} - {self.type_cours} - {self.niveau_etudiant}"
    
    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    qualite_enseignement__gte=1,
                    qualite_enseignement__lte=7,
                ),
                name="feedback_quality_1_7",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    charge_travail__gte=1,
                    charge_travail__lte=7,
                ),
                name="feedback_workload_1_7",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    interactivite__gte=1,
                    interactivite__lte=7,
                ),
                name="feedback_interactivity_1_7",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    type_cours__in=["présentiel", "distanciel", "hybride"]
                ),
                name="feedback_course_type_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    niveau_etudiant__in=["L1", "L2", "L3", "M1", "M2"]
                ),
                name="feedback_level_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(probability_satisfied__isnull=True)
                    | (
                        models.Q(probability_satisfied__gte=0)
                        & models.Q(probability_satisfied__lte=100)
                    )
                ),
                name="feedback_probability_0_100",
            ),
        ]

class ModelTraining(models.Model):
    training_date = models.DateTimeField(auto_now_add=True)
    accuracy = models.FloatField()
    dataset_size = models.IntegerField()
    model_file = models.CharField(max_length=255)
    # ✨ CORRECTION APPLIQUÉE ICI ✨
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=False)
    
    @property
    def accuracy_percent(self):
        return self.accuracy * 100

    def __str__(self):
        return f"Modèle entraîné le {self.training_date.strftime('%d/%m/%Y')} - {self.accuracy:.2%}"
    
    class Meta:
        ordering = ['-training_date']

class Notification(models.Model):
    LEVEL_CHOICES = [
        ("info", "Information"),
        ("success", "Succès"),
        ("warning", "Avertissement"),
        ("error", "Erreur"),
    ]

    EVENT_CHOICES = [
        ("auth", "Authentification"),
        ("prediction", "Prédiction"),
        ("training", "Entraînement"),
        ("data", "Données"),
        ("export", "Export"),
        ("system", "Système"),
    ]

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="satisfaction_notifications",
    )
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=500)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="info")
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES, default="system")
    target_url = models.CharField(max_length=255, blank=True, default="")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.title}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"], name="notif_user_read_idx"),
        ]

