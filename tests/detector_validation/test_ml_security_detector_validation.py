#!/usr/bin/env python3
"""
ML Security Detector Validation Tests

This module validates that the MLSecurityDetector correctly identifies
machine learning and AI security vulnerabilities.

Test Coverage:
- Data Poisoning: Training models with untrusted/unvalidated data
- Model Theft: Saving models to publicly accessible locations
- Insecure Model Serving: ML inference endpoints without authentication
- Secure ML Practices: Validated data, private model storage, authenticated endpoints
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_ml_security import MLSecurityDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestMLSecurityDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for ML Security Detector."""

    def get_detector(self):
        """Return MLSecurityDetector instance."""
        return MLSecurityDetector()

    def get_samples(self):
        """Return hand-crafted ML security test samples."""
        return [
            # ========== CRITICAL VULNERABILITIES - Data Poisoning ==========

            DetectorValidationSample(
                name="ml_data_poisoning_requests_get",
                code='''
import requests
import pandas as pd
from sklearn.linear_model import LogisticRegression

def train_model_from_url(data_url):
    # Download training data from external source
    response = requests.get(data_url)
    data = pd.read_csv(response.content)

    # Train model directly without validation
    model = LogisticRegression()
    model.fit(data[['feature1', 'feature2']], data['label'])

    return model
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_DATA_POISONING"],
                expected_score=(0, 2),
                description="CRITICAL: Training model with data from requests.get without validation",
                tags=["python", "data-poisoning", "critical", "requests"]
            ),

            DetectorValidationSample(
                name="ml_data_poisoning_user_input",
                code='''
from sklearn.ensemble import RandomForestClassifier

def train_custom_model(user_input_data, user_input_labels):
    # Training with user input without validation
    model = RandomForestClassifier()
    model.fit(user_input_data, user_input_labels)

    return model
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_DATA_POISONING"],
                expected_score=(0, 2),
                description="CRITICAL: Training with user_input without validation",
                tags=["python", "data-poisoning", "critical", "user-input"]
            ),

            DetectorValidationSample(
                name="ml_data_poisoning_download",
                code='''
import urllib.request
import tensorflow as tf

def train_neural_network(dataset_url):
    # Download training dataset
    filename, headers = urllib.request.urlretrieve(dataset_url, 'dataset.csv')

    # Load and train without validation
    dataset = tf.data.experimental.make_csv_dataset(filename, batch_size=32)

    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(10, activation='softmax')
    ])

    model.fit(dataset, epochs=10)
    return model
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_DATA_POISONING"],
                expected_score=(0, 2),
                description="CRITICAL: Training with urllib download without validation",
                tags=["python", "data-poisoning", "critical", "urllib", "tensorflow"]
            ),

            DetectorValidationSample(
                name="ml_data_poisoning_request_training",
                code='''
from flask import Flask, request
import torch
import torch.nn as nn

app = Flask(__name__)

@app.route('/train', methods=['POST'])
def train_endpoint():
    # Get training data from request
    training_data = request.json['data']
    labels = request.json['labels']

    # Train model with request data (no validation!)
    model = nn.Linear(10, 2)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)

    tensor_data = torch.tensor(training_data)
    tensor_labels = torch.tensor(labels)

    # Training loop
    output = model(tensor_data)
    loss = nn.CrossEntropyLoss()(output, tensor_labels)
    loss.backward()
    optimizer.step()

    return {'status': 'trained'}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_DATA_POISONING"],
                expected_score=(0, 2),
                description="CRITICAL: Training with request.json data without validation",
                tags=["python", "data-poisoning", "critical", "request", "pytorch"]
            ),

            # ========== HIGH VULNERABILITIES - Model Theft ==========

            DetectorValidationSample(
                name="ml_model_theft_static_directory",
                code='''
from sklearn.ensemble import GradientBoostingClassifier
import joblib

def save_trained_model(model):
    # Saving model to publicly accessible static directory
    joblib.dump(model, '/static/models/classifier.pkl')
    print("Model saved to static folder")
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_MODEL_THEFT"],
                expected_score=(1, 2),
                description="HIGH: Model saved to /static/ directory (publicly accessible)",
                tags=["python", "model-theft", "high", "static"]
            ),

            DetectorValidationSample(
                name="ml_model_theft_public_path",
                code='''
import torch

def export_model(model):
    # Save PyTorch model to public directory
    torch.save(model.state_dict(), 'public/models/model.pth')
    return 'Model exported'
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_MODEL_THEFT"],
                expected_score=(1, 2),
                description="HIGH: PyTorch model saved to public directory",
                tags=["python", "model-theft", "high", "public", "pytorch"]
            ),

            DetectorValidationSample(
                name="ml_model_theft_h5_static",
                code='''
import tensorflow as tf

def save_keras_model(model):
    # Keras model saved to static folder
    model.save('/app/static/trained_model.h5')
    print("Model saved successfully")
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_MODEL_THEFT"],
                expected_score=(1, 2),
                description="HIGH: Keras .h5 model saved to static directory",
                tags=["python", "model-theft", "high", "keras", "h5"]
            ),

            DetectorValidationSample(
                name="ml_model_theft_pickle_public",
                code='''
import pickle

def persist_model(trained_model):
    # Save pickled model to public location
    with open('public/model.pkl', 'wb') as f:
        pickle.dump(trained_model, f)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_MODEL_THEFT"],
                expected_score=(1, 2),
                description="HIGH: Pickled model saved to public location",
                tags=["python", "model-theft", "high", "pickle"]
            ),

            # ========== HIGH VULNERABILITIES - Serving Without Auth ==========

            DetectorValidationSample(
                name="ml_serving_no_auth_flask_predict",
                code='''
from flask import Flask, request, jsonify
import joblib

app = Flask(__name__)
model = joblib.load('model.pkl')

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json['features']
    prediction = model.predict([data])
    return jsonify({'prediction': prediction.tolist()})
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_SERVING_NO_AUTH"],
                expected_score=(1, 2),
                description="HIGH: Flask /predict endpoint without authentication",
                tags=["python", "serving-no-auth", "high", "flask"]
            ),

            DetectorValidationSample(
                name="ml_serving_no_auth_api_predict",
                code='''
from fastapi import FastAPI
import torch

app = FastAPI()
model = torch.load('model.pt')

@app.post('/api/predict')
async def make_prediction(data: dict):
    input_tensor = torch.tensor(data['features'])
    output = model(input_tensor)
    return {'result': output.tolist()}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_SERVING_NO_AUTH"],
                expected_score=(1, 2),
                description="HIGH: FastAPI /api/predict endpoint without authentication",
                tags=["python", "serving-no-auth", "high", "fastapi"]
            ),

            DetectorValidationSample(
                name="ml_serving_no_auth_inference_route",
                code='''
from flask import request
import tensorflow as tf

app = Flask(__name__)
model = tf.keras.models.load_model('model.h5')

@route('/inference', methods=['POST'])
def inference():
    data = request.json['input']
    result = model(data)
    return {'inference': result.numpy().tolist()}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_SERVING_NO_AUTH"],
                expected_score=(1, 2),
                description="HIGH: @route /inference endpoint without authentication",
                tags=["python", "serving-no-auth", "high", "inference"]
            ),

            DetectorValidationSample(
                name="ml_serving_no_auth_model_endpoint",
                code='''
from flask import Flask, request
import pickle

app = Flask(__name__)

@app.route('/model/predict', methods=['POST'])
def model_predict():
    with open('model.pkl', 'rb') as f:
        model = pickle.load(f)

    # Model inference without auth check
    data = request.json['data']
    prediction = model.predict([data])

    return {'prediction': prediction.tolist()}
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_SERVING_NO_AUTH"],
                expected_score=(1, 2),
                description="HIGH: Flask /model/predict endpoint without authentication",
                tags=["python", "serving-no-auth", "high", "flask"]
            ),

            # ========== SECURE SAMPLES - Validated Training Data ==========

            DetectorValidationSample(
                name="ml_secure_validated_training",
                code='''
import requests
import pandas as pd
from sklearn.linear_model import LogisticRegression

def train_model_securely(data_url):
    # Download data
    response = requests.get(data_url)
    data = pd.read_csv(response.content)

    # VALIDATE data before training
    if not validate_data_schema(data):
        raise ValueError("Data validation failed")

    # Sanitize and verify data integrity
    data = sanitize_training_data(data)

    # Now safe to train
    model = LogisticRegression()
    model.fit(data[['feature1', 'feature2']], data['label'])

    return model

def validate_data_schema(data):
    # Validation logic
    return True

def sanitize_training_data(data):
    # Sanitization logic
    return data
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Training data is validated and sanitized before use",
                tags=["python", "secure", "validation"]
            ),

            DetectorValidationSample(
                name="ml_secure_validated_user_data",
                code='''
from sklearn.ensemble import RandomForestClassifier

def train_with_validation(user_data, user_labels):
    # Validate user input before training
    if not verify_data_quality(user_data):
        raise ValueError("Data quality check failed")

    # Check for anomalies
    checked_data = check_for_poisoning(user_data)

    # Safe to train after validation
    model = RandomForestClassifier()
    model.fit(checked_data, user_labels)

    return model

def verify_data_quality(data):
    return True

def check_for_poisoning(data):
    return data
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: User data validated and checked before training",
                tags=["python", "secure", "validation", "user-input"]
            ),

            # ========== SECURE SAMPLES - Private Model Storage ==========

            DetectorValidationSample(
                name="ml_secure_private_storage",
                code='''
from sklearn.ensemble import GradientBoostingClassifier
import joblib

def save_model_securely(model):
    # Save to private directory (not /static/ or public/)
    joblib.dump(model, '/var/models/private/classifier.pkl')
    print("Model saved to private storage")
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Model saved to private directory",
                tags=["python", "secure", "private-storage"]
            ),

            DetectorValidationSample(
                name="ml_secure_encrypted_storage",
                code='''
import torch
import os

def export_model_securely(model):
    # Save to encrypted/private location
    model_path = os.path.join('/home/user/.models', 'model.pth')
    torch.save(model.state_dict(), model_path)
    return 'Model saved securely'
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: PyTorch model saved to private user directory",
                tags=["python", "secure", "private-storage", "pytorch"]
            ),

            DetectorValidationSample(
                name="ml_secure_s3_private_bucket",
                code='''
import tensorflow as tf
import boto3

def save_to_cloud(model):
    # Save to private S3 bucket (not /static/)
    model.save('/tmp/model.h5')

    s3 = boto3.client('s3')
    s3.upload_file('/tmp/model.h5', 'private-models-bucket', 'models/model.h5')
    print("Model saved to private S3 bucket")
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Model saved to private S3 bucket",
                tags=["python", "secure", "cloud", "s3"]
            ),

            # ========== SECURE SAMPLES - Authenticated Endpoints ==========

            DetectorValidationSample(
                name="ml_secure_flask_with_auth",
                code='''
from flask import Flask, request, jsonify
from flask_login import login_required
import joblib

app = Flask(__name__)
model = joblib.load('model.pkl')

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    data = request.json['features']
    prediction = model.predict([data])
    return jsonify({'prediction': prediction.tolist()})
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Flask /predict endpoint with @login_required",
                tags=["python", "secure", "authentication", "flask"]
            ),

            DetectorValidationSample(
                name="ml_secure_fastapi_with_auth",
                code='''
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
import torch

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
model = torch.load('model.pt')

@app.post('/predict')
async def make_prediction(data: dict, token: str = Depends(oauth2_scheme)):
    # Requires authentication token
    verify_auth_token(token)

    input_tensor = torch.tensor(data['features'])
    output = model(input_tensor)
    return {'result': output.tolist()}

def verify_auth_token(token):
    pass
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: FastAPI endpoint with OAuth2 authentication",
                tags=["python", "secure", "authentication", "fastapi", "oauth"]
            ),

            DetectorValidationSample(
                name="ml_secure_inference_with_check",
                code='''
from flask import request, abort
import tensorflow as tf

model = tf.keras.models.load_model('model.h5')

@route('/inference', methods=['POST'])
def inference():
    # Check authentication before inference
    if not check_auth(request):
        abort(401)

    data = request.json['input']
    result = model(data)
    return {'inference': result.numpy().tolist()}

def check_auth(req):
    return req.headers.get('Authorization') is not None
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Inference endpoint with authentication check",
                tags=["python", "secure", "authentication", "check"]
            ),

            DetectorValidationSample(
                name="ml_secure_django_auth_required",
                code='''
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import pickle

@login_required
def model_prediction(request):
    with open('/private/model.pkl', 'rb') as f:
        model = pickle.load(f)

    data = request.POST.get('data')
    prediction = model.predict([data])

    return JsonResponse({'prediction': prediction.tolist()})
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="SECURE: Django view with @login_required decorator",
                tags=["python", "secure", "authentication", "django"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="ml_edge_case_training_from_database",
                code='''
import psycopg2
from sklearn.linear_model import LinearRegression

def train_from_db():
    # Training from internal database (trusted source)
    conn = psycopg2.connect(database="internal_db")
    cursor = conn.cursor()
    cursor.execute("SELECT features, labels FROM training_data")

    data = cursor.fetchall()

    model = LinearRegression()
    model.fit([row[0] for row in data], [row[1] for row in data])

    return model
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="EDGE CASE: Training from internal database (trusted source)",
                tags=["python", "edge-case", "database"]
            ),

            DetectorValidationSample(
                name="ml_edge_case_model_logging",
                code='''
import logging
import joblib

def save_model_with_logging(model):
    # Saving to private location
    model_path = '/models/private/classifier.pkl'
    joblib.dump(model, model_path)

    # Logging is not the same as saving to public
    logging.info(f"Model saved to {model_path}")
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="EDGE CASE: Logging about model save should not trigger false positive",
                tags=["python", "edge-case", "logging"]
            ),

            DetectorValidationSample(
                name="ml_edge_case_health_check_endpoint",
                code='''
from flask import Flask, jsonify, request
import joblib

app = Flask(__name__)
model = joblib.load('model.pkl')

@app.route('/health')
def health_status():
    # Health monitoring endpoint
    return jsonify({'status': 'healthy'})

@app.route('/predict', methods=['POST'])
def predict():
    # ML prediction endpoint without authentication
    data = request.json['input']
    result = model.predict([data])
    return jsonify({'result': result.tolist()})
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["ML_SERVING_NO_AUTH"],
                expected_score=(1, 2),
                description="EDGE CASE: /predict endpoint without auth (health endpoint is separate)",
                tags=["python", "edge-case", "health-check"]
            ),

            DetectorValidationSample(
                name="ml_edge_case_offline_inference",
                code='''
import torch

def batch_predict(input_file):
    # Offline batch prediction (not a web endpoint)
    model = torch.load('/models/private/model.pt')

    with open(input_file, 'r') as f:
        data = f.read()

    predictions = model(data)
    return predictions
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="EDGE CASE: Offline batch prediction (not a web endpoint)",
                tags=["python", "edge-case", "offline"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMLSecurityDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All ML Security detector validation tests PASSED")
        print("The MLSecurityDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} ML Security detector validation tests FAILED")
        print("The MLSecurityDetector has accuracy issues that must be fixed.")
        sys.exit(1)
