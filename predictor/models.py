# predictor/models.py
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
    ]
    
    qualite_enseignement = models.IntegerField()
    charge_travail = models.IntegerField()
    interactivite = models.IntegerField()
    type_cours = models.CharField(max_length=20, choices=TYPE_COURS_CHOICES)
    niveau_etudiant = models.CharField(max_length=10, choices=NIVEAU_CHOICES)
    
    # Résultats de prédiction
    predicted_satisfaction = models.BooleanField(null=True, blank=True)
    probability_satisfied = models.FloatField(null=True, blank=True)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Avis #{self.id} - {self.type_cours} - {self.niveau_etudiant}"
    
    class Meta:
        ordering = ['-created_at']

class ModelTraining(models.Model):
    training_date = models.DateTimeField(auto_now_add=True)
    accuracy = models.FloatField()
    dataset_size = models.IntegerField()
    model_file = models.CharField(max_length=255)
    # ✨ CORRECTION APPLIQUÉE ICI ✨
    notes = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Modèle entraîné le {self.training_date.strftime('%d/%m/%Y')} - {self.accuracy:.2%}"
    
    class Meta:
        ordering = ['-training_date']