# predictor/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import StudentFeedback


class LoginForm(AuthenticationForm):
    """Formulaire de connexion Django avec widgets adaptés à l'interface."""

    username = forms.CharField(
        label="Nom d'utilisateur",
        widget=forms.TextInput(
            attrs={
                "class": "auth-input",
                "autocomplete": "username",
                "placeholder": "Votre nom d'utilisateur",
            }
        ),
    )
    password = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "autocomplete": "current-password",
                "placeholder": "Votre mot de passe",
            }
        ),
    )

    error_messages = {
        "invalid_login": "Nom d'utilisateur ou mot de passe incorrect.",
        "inactive": "Ce compte est désactivé.",
    }


class RegistrationForm(UserCreationForm):
    """Inscription avec confirmation et validation native du mot de passe Django."""

    username = forms.CharField(
        label="Nom d'utilisateur",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "auth-input",
                "autocomplete": "username",
                "placeholder": "Choisissez un nom d'utilisateur",
            }
        ),
    )
    email = forms.EmailField(
        label="Adresse e-mail",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "auth-input",
                "autocomplete": "email",
                "placeholder": "nom@exemple.com",
            }
        ),
    )
    password1 = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "autocomplete": "new-password",
                "placeholder": "Créez un mot de passe",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "auth-input",
                "autocomplete": "new-password",
                "placeholder": "Répétez le mot de passe",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cette adresse e-mail est déjà utilisée.")
        return email


class PredictionForm(forms.Form):
    # Libellés pédagogiques conservés : l'utilisateur comprend la valeur avant de choisir.
    QUALITE_CHOICES = [
        ("1", "Très insatisfait"),
        ("2", "Insatisfait"),
        ("3", "Plutôt insatisfait / Peu satisfait"),
        ("4", "Neutre / Sans opinion"),
        ("5", "Plutôt satisfait / Assez satisfait"),
        ("6", "Satisfait"),
        ("7", "Très satisfait"),
    ]

    INTERACTIVITE_CHOICES = [
        ("1", "Très non interactif / Totalement passif"),
        ("2", "Non interactif"),
        ("3", "Peu interactif / Plutôt passif"),
        ("4", "Neutre / Interaction moyenne"),
        ("5", "Plutôt interactif / Assez interactif"),
        ("6", "Interactif"),
        ("7", "Très interactif"),
    ]

    CHARGE_CHOICES = [
        ("1", "Très léger"),
        ("2", "Léger"),
        ("3", "Plutôt léger / Assez léger"),
        ("4", "Moyen / Modéré"),
        ("5", "Plutôt lourd / Assez lourd"),
        ("6", "Lourd"),
        ("7", "Très lourd"),
    ]

    TYPE_COURS_CHOICES = [
        ("présentiel", "Présentiel"),
        ("distanciel", "Distanciel"),
        ("hybride", "Hybride"),
    ]

    NIVEAU_CHOICES = [
        ("L1", "L1"),
        ("L2", "L2"),
        ("L3", "L3"),
        ("M1", "M1"),
        ("M2", "M2"),
    ]

    qualite_enseignement = forms.ChoiceField(
        label="Qualité d'enseignement",
        choices=QUALITE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    charge_travail = forms.ChoiceField(
        label="Charge de travail",
        choices=CHARGE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    interactivite = forms.ChoiceField(
        label="Interactivité du cours",
        choices=INTERACTIVITE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    type_cours = forms.ChoiceField(
        label="Type de cours",
        choices=TYPE_COURS_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    niveau_etudiant = forms.ChoiceField(
        label="Niveau étudiant",
        choices=NIVEAU_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class TrainingForm(forms.Form):
    csv_file = forms.FileField(
        label="Fichier CSV de données",
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".csv"}),
    )

    notes = forms.CharField(
        label="Notes sur l'entraînement",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Notes optionnelles sur cet entraînement...",
            }
        ),
    )


class StudentFeedbackEditForm(forms.ModelForm):
    """Édition des caractéristiques d'un avis ; la prédiction est recalculée côté serveur."""

    qualite_enseignement = forms.TypedChoiceField(
        label="Qualité d'enseignement",
        choices=PredictionForm.QUALITE_CHOICES,
        coerce=int,
    )
    charge_travail = forms.TypedChoiceField(
        label="Charge de travail",
        choices=PredictionForm.CHARGE_CHOICES,
        coerce=int,
    )
    interactivite = forms.TypedChoiceField(
        label="Interactivité",
        choices=PredictionForm.INTERACTIVITE_CHOICES,
        coerce=int,
    )
    type_cours = forms.ChoiceField(
        label="Type de cours",
        choices=PredictionForm.TYPE_COURS_CHOICES,
    )
    niveau_etudiant = forms.ChoiceField(
        label="Niveau étudiant",
        choices=PredictionForm.NIVEAU_CHOICES,
    )

    class Meta:
        model = StudentFeedback
        fields = [
            "qualite_enseignement",
            "charge_travail",
            "interactivite",
            "type_cours",
            "niveau_etudiant",
        ]
