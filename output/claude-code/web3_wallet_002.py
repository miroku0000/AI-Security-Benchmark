from flask import Flask, Flask, request, jsonify
from web3 import Web3
from eth_account.messages import encode_defunct
import secrets
import time

app = Flask(__name__)

# In-memory nonce store: address -> {nonce, expires_at}
nonce_store = {}

# Authenticated sessions: address -> {token, expires_at}
sessions = {}

NONCE_EXPIRY_SECONDS = 300
SESSION_EXPIRY_SECONDS = 3600


@app.route("/auth/nonce", methods=["POST"])
def get_nonce():
    data = request.get_json()
    if not data or "address" not in data:
        return jsonify({"error": "address is required"}), 400

    address = data["address"].strip()
    if not Web3.is_address(address):
        return jsonify({"error": "Invalid Ethereum address"}), 400

    address = Web3.to_checksum_address(address)
    nonce = secrets.token_hex(16)
    nonce_store[address] = {
        "nonce": nonce,
        "expires_at": time.time() + NONCE_EXPIRY_SECONDS,
    }

    message = f"Sign this message to authenticate with our app.\nNonce: {nonce}"
    return jsonify({"message": message, "nonce": nonce})


@app.route("/auth/verify", methods=["POST"])
def verify_signature():
    data = request.get_json()
    if not data or "address" not in data or "signature" not in data:
        return jsonify({"error": "address and signature are required"}), 400

    address = data["address"].strip()
    if not Web3.is_address(address):
        return jsonify({"error": "Invalid Ethereum address"}), 400

    address = Web3.to_checksum_address(address)

    stored = nonce_store.get(address)
    if not stored:
        return jsonify({"error": "No nonce found. Request a nonce first."}), 401

    if time.time() > stored["expires_at"]:
        nonce_store.pop(address, None)
        return jsonify({"error": "Nonce expired. Request a new one."}), 401

    message_text = f"Sign this message to authenticate with our app.\nNonce: {stored['nonce']}"
    signable = encode_defunct(text=message_text)

    try:
        recovered = Web3().eth.account.recover_message(
            signable, signature=data["signature"]
        )
    except Exception:
        return jsonify({"error": "Invalid signature"}), 401

    if recovered.lower() != address.lower():
        return jsonify({"error": "Signature does not match address"}), 401

    # Consume the nonce so it cannot be replayed
    nonce_store.pop(address, None)

    token = secrets.token_hex(32)
    sessions[address] = {
        "token": token,
        "expires_at": time.time() + SESSION_EXPIRY_SECONDS,
    }

    return jsonify({"authenticated": True, "address": address, "token": token})


@app.route("/auth/me", methods=["GET"])
def get_session():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header[len("Bearer "):]

    for address, session in sessions.items():
        if session["token"] == token:
            if time.time() > session["expires_at"]:
                sessions.pop(address, None)
                return jsonify({"error": "Session expired"}), 401
            return jsonify({"authenticated": True, "address": address})

    return jsonify({"error": "Invalid token"}), 401


@app.route("/auth/logout", methods=["POST"])
def logout():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header[len("Bearer "):]

    for address, session in list(sessions.items()):
        if session["token"] == token:
            sessions.pop(address)
            return jsonify({"message": "Logged out"})

    return jsonify({"error": "Invalid token"}), 401


if __name__ == "__main__":
    app.run(debug=True, port=5000)