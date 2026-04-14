import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import os
import json

def train_model():
    data_path = 'data/iot_sensor_data.csv'
    if not os.path.exists(data_path):
        print(f"Dataset not found at {data_path}. Please run generate_data.py first.")
        return
        
    print("Loading dataset...")
    data = pd.read_csv(data_path)
    
    # Features and labels
    X = data[['temperature', 'vibration', 'current']]
    y = data['failure']
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Random Forest model...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    print("Evaluating model...")
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    print("="*40)
    print(f"Model Accuracy: {acc * 100:.2f}%")
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    print("="*40)
    
    # Save the model and metrics
    os.makedirs('models', exist_ok=True)
    model_path = 'models/model.pkl'
    joblib.dump(model, model_path)
    
    metrics = {
        "accuracy": round(acc * 100, 2),
        "feature_importances": {
            "Temperature": round(model.feature_importances_[0] * 100, 2),
            "Vibration": round(model.feature_importances_[1] * 100, 2),
            "Current Load": round(model.feature_importances_[2] * 100, 2)
        }
    }
    with open('models/metrics.json', 'w') as f:
        json.dump(metrics, f)
        
    print(f"Success: Model and Matrix saved successfully at {model_path}")

if __name__ == '__main__':
    train_model()
