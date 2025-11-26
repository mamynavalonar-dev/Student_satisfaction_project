# predictor/views.py - Fichier mis à jour avec les vues d'authentification

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
# Nouveaux imports pour l'authentification
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import pandas as pd
import json
from datetime import datetime
from .models import StudentFeedback, ModelTraining
from .forms import PredictionForm, TrainingForm
from .neural_network_model import train_model, predict_satisfaction, load_current_model

# NOUVELLE VUE : Connexion et Inscription
def login_register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        # Logique d'inscription
        if form_type == 'register':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Ce nom d\'utilisateur existe déjà.', 'register_error')
                return redirect('login_register')
            
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            login(request, user)
            messages.success(request, f'✅ Inscription réussie ! Bienvenue, {username}.')
            return redirect('home')

        # Logique de connexion
        elif form_type == 'login':
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.', 'login_error')
                return redirect('login_register')

    return render(request, 'predictor/login_register.html')


# NOUVELLE VUE : Déconnexion
def logout_view(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login_register')


# VUES EXISTANTES : Maintenant protégées par @login_required
# L'utilisateur doit être connecté pour y accéder.
@login_required(login_url='login_register')
def home(request):
    """Page d'accueil avec statistiques"""
    total_feedbacks = StudentFeedback.objects.count()
    satisfied_count = StudentFeedback.objects.filter(predicted_satisfaction=True).count()
 
    model_loaded = load_current_model() is not None
    
    context = {
        'total_feedbacks': total_feedbacks,
        'satisfied_count': satisfied_count,
        'model_loaded': model_loaded,
    }
    return render(request, 'predictor/home.html', context)

@login_required(login_url='login_register')
def predict(request):
    """Page de prédiction"""
    if request.method == 'POST':
        form = PredictionForm(request.POST)
        if form.is_valid():
           
            try:
                # Préparer les données pour la prédiction
                input_data = {
                    'qualite_enseignement': int(form.cleaned_data['qualite_enseignement']),
                    'charge_travail': int(form.cleaned_data['charge_travail']),
                 
                    'interactivite': int(form.cleaned_data['interactivite']),
                    'type_cours': form.cleaned_data['type_cours'],
                    'niveau_etudiant': form.cleaned_data['niveau_etudiant'],
                }
                
                # Charger le modèle
   
                model_data = load_current_model()
                if model_data:
                    prediction_result = predict_satisfaction(model_data, input_data)
                    
                    # Sauvegarder le feedback dans la base de données
                    feedback = StudentFeedback(
                        qualite_enseignement=input_data['qualite_enseignement'],
                        charge_travail=input_data['charge_travail'],
                        interactivite=input_data['interactivite'],
   
                        type_cours=input_data['type_cours'],
                        niveau_etudiant=input_data['niveau_etudiant'],
                        predicted_satisfaction=bool(prediction_result['prediction']),
                        probability_satisfied=prediction_result['probability_satisfied']
       
                    )
                    feedback.save()
                    
                    context = {
                        'form': PredictionForm(),
                        'prediction_result': prediction_result,
                        'input_data': input_data,
                    }
                    return render(request, 'predictor/predict.html', context)
       
                else:
                    messages.error(request, "⚠ Aucun modèle n'est chargé. Veuillez d'abord entraîner un modèle.")
            except Exception as e:
                messages.error(request, f"⚠ Erreur lors de la prédiction: {str(e)}")
    else:
        form = PredictionForm()
    
    return render(request, 'predictor/predict.html', {'form': form})

@login_required(login_url='login_register')
def train_model_view(request):
    """Page d'entraînement du modèle"""
    trainings = ModelTraining.objects.all().order_by('-training_date')[:10]
    model_loaded = load_current_model() is not None
    
    # Préparer l'historique d'entraînement pour le graphique
    training_history = {
        'dates': [],
        'accuracies': []
    }
    
    for training in trainings:
        training_history['dates'].append(training.training_date.strftime("%Y-%m-%d %H:%M"))
        training_history['accuracies'].append(float(training.accuracy * 100))
    
    if request.method == 'POST':
        form = TrainingForm(request.POST, request.FILES)
        if form.is_valid():
      
            try:
                csv_file = request.FILES['csv_file']
                
                # Vérifier l'extension du fichier
                if not csv_file.name.endswith('.csv'):
                    messages.error(request, "⚠ Le fichier doit être au format CSV.")
                    return redirect('train_model')
                
                # Lire le fichier CSV
                df = pd.read_csv(csv_file)
                
   
                # Vérifier les colonnes nécessaires
                required_columns = ['qualite_enseignement', 'charge_travail', 'interactivite', 'type_cours', 'niveau_etudiant', 'satisfaction']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    messages.error(request, f"⚠ Colonnes manquantes: {', '.join(missing_columns)}")
                    return redirect('train_model')
                
                # Entraîner le modèle
                accuracy, model_path = train_model(df)
                
                # Sauvegarder l'entraînement dans la base de données
                training = ModelTraining(
                    accuracy=accuracy,
                    dataset_size=len(df),
   
                    model_file=model_path,
                    notes=form.cleaned_data['notes'],
                    is_active=True
                )
                training.save()
           
                # Désactiver les autres modèles
                ModelTraining.objects.exclude(id=training.id).update(is_active=False)
                
                messages.success(request, f"✅ Modèle entraîné avec succès! Précision: {accuracy:.2%}")
                return redirect('train_model')
                
            except Exception as e:
                messages.error(request, f"⚠ Erreur lors de l'entraînement: {str(e)}")
    else:
        form = TrainingForm()
    
    context = {
        'form': form,
        'trainings': trainings,
        'model_loaded': model_loaded,
        'training_history': json.dumps(training_history),
    }
    return render(request, 'predictor/train.html', context)

@login_required(login_url='login_register')
def statistics(request):
    """Page des statistiques - VERSION CORRIGÉE"""
    # ... (le reste de la fonction est inchangé) ...
    feedbacks = StudentFeedback.objects.all()
    total = feedbacks.count()
    satisfied = feedbacks.filter(predicted_satisfaction=True).count()
    unsatisfied = total - satisfied
    satisfaction_rate = (satisfied / total * 100) if total > 0 else 0
    stats = {'total': total, 'satisfied': satisfied, 'unsatisfied': unsatisfied, 'satisfaction_rate': satisfaction_rate}
    type_stats = {}
    type_cours_list = ['présentiel', 'distanciel', 'hybride']
    for type_cours in type_cours_list:
        type_feedbacks = feedbacks.filter(type_cours=type_cours)
        type_total = type_feedbacks.count()
        type_satisfied = type_feedbacks.filter(predicted_satisfaction=True).count()
        type_rate = (type_satisfied / type_total * 100) if type_total > 0 else 0
        type_stats[type_cours] = {'total': type_total, 'satisfied': type_satisfied, 'unsatisfied': type_total - type_satisfied, 'rate': type_rate}
    niveau_stats = {}
    niveau_list = ['L1', 'L2', 'L3']
    for niveau in niveau_list:
        niveau_feedbacks = feedbacks.filter(niveau_etudiant=niveau)
        niveau_total = niveau_feedbacks.count()
        niveau_satisfied = niveau_feedbacks.filter(predicted_satisfaction=True).count()
        niveau_rate = (niveau_satisfied / niveau_total * 100) if niveau_total > 0 else 0
        niveau_stats[niveau] = {'total': niveau_total, 'satisfied': niveau_satisfied, 'unsatisfied': niveau_total - niveau_satisfied, 'rate': niveau_rate}
    charts_data = {
        'satisfaction_pie': {'labels': ['Satisfaits', 'Non Satisfaits'], 'data': [satisfied, unsatisfied]},
        'type_cours_bar': {'labels': list(type_stats.keys()), 'satisfied': [type_stats[k]['satisfied'] for k in type_stats.keys()], 'unsatisfied': [type_stats[k]['unsatisfied'] for k in type_stats.keys()]},
        'niveau_bar': {'labels': list(niveau_stats.keys()), 'rates': [niveau_stats[k]['rate'] for k in niveau_stats.keys()]}
    }
    context = {'stats': stats, 'type_stats': type_stats, 'niveau_stats': niveau_stats, 'charts_data_json': json.dumps(charts_data)}
    return render(request, 'predictor/statistics.html', context)

@login_required(login_url='login_register')
def data_management(request):
    """Page de gestion des données"""
    feedbacks = StudentFeedback.objects.all().order_by('-created_at')
    total_count = feedbacks.count()
    satisfied_count = feedbacks.filter(predicted_satisfaction=True).count()
    paginator = Paginator(feedbacks, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'feedbacks': page_obj, 'total_count': total_count, 'satisfied_count': satisfied_count}
    return render(request, 'predictor/data.html', context)

@login_required(login_url='login_register')
def export_data(request):
    """Export des données en CSV"""
    try:
        feedbacks = StudentFeedback.objects.all()
        data = []
        for feedback in feedbacks:
            data.append({
                'id': feedback.id,
                'qualite_enseignement': feedback.qualite_enseignement,
                'charge_travail': feedback.charge_travail,
                'interactivite': feedback.interactivite,
                'type_cours': feedback.type_cours,
                'niveau_etudiant': feedback.niveau_etudiant,
                'predicted_satisfaction': feedback.predicted_satisfaction,
                'probability_satisfied': feedback.probability_satisfied,
                'created_at': feedback.created_at,
            })
        df = pd.DataFrame(data)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="avis_etudiants_export.csv"'
        df.to_csv(response, index=False, encoding='utf-8-sig')
        return response
    except Exception as e:
        messages.error(request, f"⚠ Erreur lors de l'export: {str(e)}")
        return redirect('data_management')