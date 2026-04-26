# spam_detector_train.py
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

spam_emails = [
    "Click here to win free money now!!!",
    "Congratulations you won the lottery",
    "Buy cheap medications online",
    "Enlarge your package quickly",
    "Work from home and earn thousands",
    "Free money transfer from Nigeria",
    "You have been selected for a prize",
    "Get rich quick schemes here",
    "Claim your inheritance today",
    "Limited time offer on fake watches",
    "Join our pyramid scheme",
    "Meet hot singles in your area",
    "Viagra online no prescription needed",
    "Casino with huge jackpots waiting",
    "Your bank account has been compromised",
    "Verify your account information immediately",
    "Western Union money transfer available",
    "Cheap designer bags authentic quality",
    "Forex trading guaranteed profits",
    "Your password needs to be reset urgently",
    "You are a winner click to claim",
    "Awesome deals on luxury items",
    "Get paid to take surveys online",
    "Investment opportunity in oil fields",
    "Instant cash loans no credit check",
    "Hidden wealth waiting for you",
    "Refinance your mortgage today save money",
    "Stock tips that guarantee returns",
    "Unbelievable savings on electronics",
    "Your credit card needs verification",
]

ham_emails = [
    "Hi John, how are you doing today",
    "Meeting scheduled for tomorrow at 2pm",
    "Thanks for your email, I will get back to you soon",
    "Please find attached the document you requested",
    "Can we reschedule our call for next week",
    "Great work on the project presentation",
    "I enjoyed our conversation at the conference",
    "Just checking in to see how things are going",
    "The quarterly report is ready for review",
    "Let me know if you have any questions",
    "Looking forward to hearing from you",
    "Thanks for the update on the status",
    "See you at the meeting tomorrow morning",
    "I have completed the analysis you asked for",
    "Please confirm receipt of this email",
    "Here are the files for the new project",
    "Lunch tomorrow at noon sounds good to me",
    "I appreciate your feedback on this",
    "The deadline for the proposal is Friday",
    "Can you send me the latest version",
    "Thanks for inviting me to the event",
    "I will be traveling next week",
    "Please review the attached proposal",
    "Let me know what time works best for you",
    "The agenda for todays meeting is attached",
    "I have a few questions about the contract",
    "Great to connect with you on LinkedIn",
    "The data shows a 20 percent increase",
    "Our team achieved the quarterly target",
    "I wanted to follow up on our discussion",
]

X = spam_emails + ham_emails
y = [1] * len(spam_emails) + [0] * len(ham_emails)

model = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=100, stop_words='english', lowercase=True)),
    ('classifier', LogisticRegression(max_iter=200, random_state=42))
])

model.fit(X, y)

os.makedirs('spam_detector_model', exist_ok=True)
with open('spam_detector_model/spam_detector.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Model trained and saved")

from sklearn.metrics import accuracy_score, precision_score, recall_score
y_pred = model.predict(X)
print(f"Accuracy: {accuracy_score(y, y_pred):.4f}")
print(f"Precision: {precision_score(y, y_pred):.4f}")
print(f"Recall: {recall_score(y, y_pred):.4f}")