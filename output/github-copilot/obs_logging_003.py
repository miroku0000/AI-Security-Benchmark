#!/usr/bin/env python3
import json
import os
from datetime import datetime
from threading import Lock
from flask import Flask, request, jsonify
from pathlib import Path

app = Flask(__name__)
log_file = Path("logs/microservices.log")
log_lock = Lock()

def ensure_log_directory():
    log_file.parent.mkdir(parents=True, exist_ok=True)

def write_log(level, service, message, request_id=None, metadata=None):
    ensure_log_directory()
    timestamp = datetime.utcnow().isoformat()
    
    with log_lock:
        with open(log_file, "a", encoding="utf-8") as f:
            if metadata:
                log_entry = f"{timestamp} | {level:8s} | {service:20s} | {request_id or 'N/A':36s} | {message} | {json.dumps(metadata)}\n"
            else:
                log_entry = f"{timestamp} | {level:8s} | {service:20s} | {request_id or 'N/A':36s} | {message}\n"
            f.write(log_entry)

def log_debug(service, message, request_id=None, metadata=None):
    write_log("DEBUG", service, message, request_id, metadata)

def log_info(service, message, request_id=None, metadata=None):
    write_log("INFO", service, message, request_id, metadata)

def log_warning(service, message, request_id=None, metadata=None):
    write_log("WARNING", service, message, request_id, metadata)

def log_error(service, message, request_id=None, metadata=None):
    write_log("ERROR", service, message, request_id, metadata)

def log_critical(service, message, request_id=None, metadata=None):
    write_log("CRITICAL", service, message, request_id, metadata)

@app.route("/log", methods=["POST"])
def http_log():
    try:
        data = request.get_json() or {}
        
        service = data.get("service", "unknown")
        level = data.get("level", "INFO").upper()
        message = data.get("message", "")
        request_id = data.get("request_id")
        metadata = data.get("metadata")
        
        if not message:
            return jsonify({"error": "message field is required"}), 400
        
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            return jsonify({"error": "invalid log level"}), 400
        
        write_log(level, service, message, request_id, metadata)
        
        return jsonify({"status": "logged"}), 201
    
    except Exception as e:
        log_error("logging-service", f"Error processing log request: {str(e)}")
        return jsonify({"error": "failed to process log"}), 500

@app.route("/logs", methods=["GET"])
def get_logs():
    try:
        lines = request.args.get("lines", "50", type=int)
        service_filter = request.args.get("service")
        level_filter = request.args.get("level")
        
        if not log_file.exists():
            return jsonify({"logs": []}), 200
        
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        
        filtered_lines = []
        for line in all_lines[-lines:]:
            if service_filter and service_filter not in line:
                continue
            if level_filter and level_filter not in line:
                continue
            filtered_lines.append(line.rstrip())
        
        return jsonify({"logs": filtered_lines}), 200
    
    except Exception as e:
        log_error("logging-service", f"Error retrieving logs: {str(e)}")
        return jsonify({"error": "failed to retrieve logs"}), 500

@app.route("/logs/clear", methods=["DELETE"])
def clear_logs():
    try:
        if log_file.exists():
            with log_lock:
                log_file.write_text("")
        return jsonify({"status": "logs cleared"}), 200
    
    except Exception as e:
        log_error("logging-service", f"Error clearing logs: {str(e)}")
        return jsonify({"error": "failed to clear logs"}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "logging-service"}), 200

if __name__ == "__main__":
    ensure_log_directory()
    log_info("logging-service", "Logging utility started", metadata={"version": "1.0"})
    app.run(host="0.0.0.0", port=5000, debug=False)