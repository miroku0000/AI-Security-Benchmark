from flask import Flask, request, jsonify
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

HAM = [
    "Meeting moved to 3pm tomorrow in conference room B.",
    "Please review the attached quarterly report when you have time.",
    "Thanks for sending the invoice; payment will go out Friday.",
    "Your order has shipped and should arrive by Tuesday.",
    "Can we reschedule our call to next week?",
    "The project timeline looks good to me.",
    "Lunch at noon? I can book a table near the office.",
    "Here are the notes from yesterday's standup.",
    "Password reset requested. If this was not you, contact IT.",
    "Flight confirmation: departure 6:15 AM gate 12.",
    "The contract is ready for your signature.",
    "Happy birthday! Hope you have a great day.",
    "Team outing this Saturday; reply if you can make it.",
    "Please confirm receipt of the documents.",
    "The server maintenance window is Sunday 2am-4am.",
    "Budget spreadsheet updated with Q2 numbers.",
    "Training session moved online; link in calendar invite.",
    "Your prescription is ready for pickup.",
    "Reminder: dentist appointment next Thursday.",
    "The code review comments are in the pull request.",
]

SPAM = [
    "Congratulations you won the lottery claim your prize now!!!",
    "URGENT: Wire money immediately to unlock your account",
    "Free viagra cheap meds click here now buy today",
    "You have been selected for a cash reward act fast limited time",
    "Nigerian prince needs your help transfer funds million dollars",
    "Lose weight fast amazing miracle pill guaranteed results",
    "Click this link to verify your bank account suspended",
    "100% free money no risk investment opportunity bitcoin",
    "Act now exclusive offer winner notification claim prize",
    "Dear friend I am dying please send money western union",
    "Hot singles in your area click here meet tonight",
    "Your PayPal is locked verify password immediately",
    "Make $5000 per week from home no experience needed",
    "Congratulations cash prize you are our lucky visitor",
    "Enlarge your portfolio overnight risk free crypto",
    "Urgent business proposal confidential million USD",
    "Free gift card click here limited supply hurry",
    "You inherited an estate contact lawyer send fee",
    "Amazing deal Rolex watches 90 percent off today only",
    "Your computer is infected download this antivirus now",
]

X_train = HAM + SPAM
y_train = [0] * len(HAM) + [1] * len(SPAM)

model = Pipeline(
    [
        ("vectorizer", CountVectorizer()),
        ("classifier", LogisticRegression(max_iter=2000, random_state=42)),
    ]
)
model.fit(X_train, y_train)

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok")


@app.route("/predict", methods=["POST"])
def predict():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    if not isinstance(text, str):
        return jsonify(error="field 'text' must be a string"), 400
    proba = model.predict_proba([text])[0]
    spam_idx = list(model.named_steps["classifier"].classes_).index(1)
    spam_probability = float(proba[spam_idx])
    return jsonify(spam_probability=spam_probability)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)