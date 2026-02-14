# models/eligibility_model.py
# This file now creates, saves, and uses a dummy ML model from a .pkl file.

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
import os

MODEL_PATH = 'model.pkl'

def train_and_save_dummy_model():
    """
    Creates a simple logistic regression model and saves it to a .pkl file.
    This function is for demonstration purposes to ensure a model file exists.
    """
    print(f"'{MODEL_PATH}' not found. Training and saving a new dummy model.")
    # Dummy data: X = number of KTs, y = eligibility (1 for eligible, 0 for not)
    # Rule: <= 4 KTs is eligible.
    X = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8]).reshape(-1, 1)
    y = np.array([1, 1, 1, 1, 1, 0, 0, 0, 0])

    # Create and train the model
    model = LogisticRegression()
    model.fit(X, y)

    # Save the model to the file
    joblib.dump(model, MODEL_PATH)
    print(f"Dummy model saved to '{MODEL_PATH}'.")

# --- Model Loading ---
# Check if the model file exists. If not, create it.
if not os.path.exists(MODEL_PATH):
    train_and_save_dummy_model()

# Load the trained model from the .pkl file
try:
    model = joblib.load(MODEL_PATH)
    print("ML model loaded successfully from 'model.pkl'.")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

def predict_eligibility(num_kts: int) -> str:
    """
    Predicts academic eligibility using the loaded machine learning model.

    Args:
        num_kts (int): The number of KTs (backlogs) a student has.

    Returns:
        str: A string indicating "Eligible" or "Not Eligible".
    """
    if model is None:
        return "Model not available."

    if not isinstance(num_kts, int) or num_kts < 0:
        return "Invalid Input"

    try:
        # The model expects a 2D array as input, so we reshape the single value
        input_data = np.array([num_kts]).reshape(1, -1)
        
        # Get the prediction from the model (will be 0 or 1)
        prediction = model.predict(input_data)

        # Return the result as a user-friendly string
        if prediction[0] == 1:
            return "Eligible for Next Year"
        else:
            return "Not Eligible for Next Year"
            
    except Exception as e:
        print(f"Error during prediction: {e}")
        return "Error making prediction."