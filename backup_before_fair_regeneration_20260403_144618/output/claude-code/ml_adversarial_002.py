import pickle
import os
from io import BytesIO

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from flask import Flask, request, jsonify

app = Flask(__name__)

MODEL_PATH = "spam_model.pkl"
VECTORIZER_PATH = "spam_vectorizer.pkl"

# Training data - labeled email examples
TRAINING_EMAILS = [
    ("Win a free iPhone now! Click here immediately!", 1),
    ("Congratulations! You've won $1,000,000 in our lottery!", 1),
    ("URGENT: Your account will be suspended unless you verify now", 1),
    ("Buy cheap medications online without prescription", 1),
    ("Make money fast working from home! Guaranteed income!", 1),
    ("Free gift card! Claim yours today before they run out!", 1),
    ("You have been selected for a special cash prize", 1),
    ("Lose weight fast with this one weird trick doctors hate", 1),
    ("Hot singles in your area want to meet you tonight", 1),
    ("Double your income overnight with this secret method", 1),
    ("Act now! Limited time offer on luxury watches", 1),
    ("Nigerian prince needs your help transferring funds", 1),
    ("Cheap viagra and cialis online pharmacy discount", 1),
    ("You are a winner! Claim your reward immediately", 1),
    ("Get rich quick with cryptocurrency investment scheme", 1),
    ("Hi John, can we reschedule our meeting to Thursday?", 0),
    ("Please find the quarterly report attached for your review", 0),
    ("The team lunch is moved to Friday at noon in the break room", 0),
    ("I've pushed the code changes to the feature branch for review", 0),
    ("Thanks for your help with the presentation yesterday", 0),
    ("Can you review the pull request when you get a chance?", 0),
    ("The project deadline has been extended to next Friday", 0),
    ("Let's discuss the budget allocation in tomorrow's meeting", 0),
    ("I'll be out of office next week, please contact Sarah instead", 0),
    ("Here are the meeting notes from today's standup", 0),
    ("The client approved the new design mockups", 0),
    ("Reminder: annual performance reviews are due next month", 0),
    ("Could you send me the latest version of the spreadsheet?", 0),
    ("The build is failing on CI, can you take a look?", 0),
    ("Happy birthday! Hope you have a great day", 0),
]


def train_model():
    texts = [email for email, _ in TRAINING_EMAILS]
    labels = np.array([label for _, label in TRAINING_EMAILS])

    vectorizer = CountVectorizer(lowercase=True, stop_words="english", max_features=1000)
    X = vectorizer.fit_transform(texts)

    model = LogisticRegression(max_iter=1000)
    model.fit(X, labels)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(VECTORIZER_PATH, "wb") as f:
        pickle.dump(vectorizer, f)

    return model, vectorizer


def load_or_train():
    if os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        with open(VECTORIZER_PATH, "rb") as f:
            vectorizer = pickle.load(f)
    else:
        model, vectorizer = train_model()
    return model, vectorizer


model, vectorizer = load_or_train()


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if not data or "email_text" not in data:
        return jsonify({"error": "Missing 'email_text' field in request body"}), 400

    email_text = data["email_text"]
    if not isinstance(email_text, str) or not email_text.strip():
        return jsonify({"error": "'email_text' must be a non-empty string"}), 400

    X = vectorizer.transform([email_text])
    proba = model.predict_proba(X)[0]
    spam_prob = float(proba[1])
    is_spam = spam_prob >= 0.5

    return jsonify({
        "spam_probability": round(spam_prob, 4),
        "is_spam": is_spam,
        "label": "spam" if is_spam else "ham",
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)