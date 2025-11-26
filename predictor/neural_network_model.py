# predictor/neural_network_model.py
import pandas as pd
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os
from datetime import datetime
from .models import ModelTraining 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def preprocess_data(df):
    """Prétraite les données pour l'entraînement du modèle."""
    data = df.copy()
    
    if 'satisfaction' in data.columns:
        if data['satisfaction'].dtype == 'object':
            data['satisfaction'] = data['satisfaction'].map({'satisfait': 1, 'non satisfait': 0, '1': 1, '0': 0})
        data['satisfaction'] = data['satisfaction'].astype(int)
    
    label_encoders = {}
    categorical_columns = ['type_cours', 'niveau_etudiant']
    
    for col in categorical_columns:
        if col in data.columns:
            le = LabelEncoder()
            data[col] = le.fit_transform(data[col])
            label_encoders[col] = le
    
    X = data.drop('satisfaction', axis=1)
    y = data['satisfaction']
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    return X_scaled, y, scaler, label_encoders

def train_model(df):
    """Entraîne un modèle de réseau de neurones."""
    try:
        X, y, scaler, label_encoders = preprocess_data(df)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            solver='adam',
            alpha=0.001,  # ✨ CORRECTION: Alpha réduit pour une meilleure régularisation
            max_iter=1000,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1
        )
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_filename = f'student_satisfaction_model_{timestamp}.joblib'
        model_path = os.path.join(BASE_DIR, model_filename)

        model_data = {
            'model': model,
            'scaler': scaler,
            'label_encoders': label_encoders,
            'accuracy': accuracy,
            'training_date': datetime.now(),
            'feature_names': df.drop('satisfaction', axis=1).columns.tolist()
        }
        
        joblib.dump(model_data, model_path)
        return accuracy, model_path
        
    except Exception as e:
        raise Exception(f"Erreur lors de l'entraînement: {str(e)}")

def load_current_model():
    """Charge le modèle actuellement actif depuis la base de données."""
    try:
        active_training = ModelTraining.objects.filter(is_active=True).latest('training_date')
        model_path = active_training.model_file
        if os.path.exists(model_path):
            return joblib.load(model_path)
        return None
    except ModelTraining.DoesNotExist:
        return None
    except Exception:
        return None

def predict_satisfaction(model_data, input_data):
    """Prédit la satisfaction à partir des données d'entrée."""
    try:
        model = model_data['model']
        scaler = model_data['scaler']
        label_encoders = model_data['label_encoders']
        
        input_df = pd.DataFrame([input_data])
        
        for col, le in label_encoders.items():
            if col in input_df.columns:
                classes = list(le.classes_)
                if input_df[col].iloc[0] in classes:
                    input_df[col] = le.transform(input_df[col].values)
                else:
                    input_df[col] = -1 # Gère les catégories inconnues
        
        if 'feature_names' in model_data:
            input_df = input_df[model_data['feature_names']]
        
        input_scaled = scaler.transform(input_df)
        
        prediction = model.predict(input_scaled)[0]
        probability = model.predict_proba(input_scaled)[0]
        
        # ======================================================================
        # ✨ CORRECTION : Le dictionnaire retourné est plus clair et complet ✨
        # ======================================================================
        if prediction == 1:
            satisfaction_text = 'Satisfait'
            prediction_probability = probability[1]
        else:
            satisfaction_text = 'Non satisfait'
            prediction_probability = probability[0]

        return {
            'prediction': int(prediction),
            'probability_satisfied': float(probability[1] * 100),
            'probability_unsatisfied': float(probability[0] * 100),
            'satisfaction_text': satisfaction_text,
            'prediction_probability': float(prediction_probability * 100),
        }
        
    except Exception as e:
        raise Exception(f"Erreur lors de la prédiction: {str(e)}")