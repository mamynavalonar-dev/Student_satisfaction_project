# predictor/forms.py
from django import forms

class PredictionForm(forms.Form):
    # Qualité d'enseignement avec libellés textuels
    QUALITE_CHOICES = [
        ('1', 'Très insatisfait'),
        ('2', 'Insatisfait'),
        ('3', 'Plutôt insatisfait / Peu satisfait'),
        ('4', 'Neutre / Sans opinion'),
        ('5', 'Plutôt satisfait / Assez satisfait'),
        ('6', 'Satisfait'),
        ('7', 'Très satisfait'),
    ]
    
    # Interactivité avec libellés textuels
    INTERACTIVITE_CHOICES = [
        ('1', 'Très non interactif / Totalement passif'),
        ('2', 'Non interactif'),
        ('3', 'Peu interactif / Plutôt passif'),
        ('4', 'Neutre / Interaction moyenne'),
        ('5', 'Plutôt interactif / Assez interactif'),
        ('6', 'Interactif'),
        ('7', 'Très interactif'),
    ]
    
    # Charge de travail avec libellés textuels
    CHARGE_CHOICES = [
        ('1', 'Très léger'),
        ('2', 'Léger'),
        ('3', 'Plutôt léger / Assez léger'),
        ('4', 'Moyen / Modéré'),
        ('5', 'Plutôt lourd / Assez lourd'),
        ('6', 'Lourd'),
        ('7', 'Très lourd'),
    ]
    
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
    
    qualite_enseignement = forms.ChoiceField(
        label="Qualité d'enseignement",
        choices=QUALITE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    charge_travail = forms.ChoiceField(
        label="Charge de travail",
        choices=CHARGE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    interactivite = forms.ChoiceField(
        label="Interactivité du cours",
        choices=INTERACTIVITE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    type_cours = forms.ChoiceField(
        label="Type de cours",
        choices=TYPE_COURS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    niveau_etudiant = forms.ChoiceField(
        label="Niveau étudiant",
        choices=NIVEAU_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class TrainingForm(forms.Form):
    csv_file = forms.FileField(
        label="Fichier CSV de données",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'})
    )
    
    notes = forms.CharField(
        label="Notes sur l'entraînement",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': 'Notes optionnelles sur cet entraînement...'
        })
    )