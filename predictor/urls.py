# predictor/urls.py
# Fichier mis à jour pour l'authentification

from django.urls import path
from . import views

urlpatterns = [
    # Nouvelle page d'accueil qui est maintenant la page de connexion/inscription
    path('', views.login_register_view, name='login_register'),
    
    # L'ancienne page d'accueil est maintenant le "tableau de bord"
    path('dashboard/', views.home, name='home'),
    
    # Route pour la déconnexion
    path('logout/', views.logout_view, name='logout'),
    
    # Routes existantes de l'application
    path('predict/', views.predict, name='predict'),
    path('train/', views.train_model_view, name='train_model'),
    path('statistics/', views.statistics, name='statistics'),
    path('data/', views.data_management, name='data_management'),
    path('export/', views.export_data, name='export_data'),
]