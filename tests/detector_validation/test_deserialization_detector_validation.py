#!/usr/bin/env python3
"""
Deserialization Detector Validation Tests

This module validates that the DeserializationDetector correctly identifies
insecure deserialization vulnerabilities and secure deserialization patterns.

Test Coverage:
- Python: pickle.load/loads, json (safe), yaml.safe_load vs yaml.load
- JavaScript: JSON.parse (safe), eval (dangerous), node-serialize
- Java: ObjectInputStream, safe alternatives
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_deserialization import DeserializationDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestDeserializationDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for Deserialization Detector."""

    def get_detector(self):
        """Return DeserializationDetector instance."""
        return DeserializationDetector()

    def get_samples(self):
        """Return hand-crafted deserialization test samples."""
        return [
            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="deserial_python_pickle_load_user_data",
                code='''
import pickle
from flask import Flask, request

app = Flask(__name__)

@app.route('/load', methods=['POST'])
def load_data():
    data = request.data
    # VULNERABLE: pickle.loads() with user input
    obj = pickle.loads(data)
    return str(obj)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="Deserialization via pickle.loads() with user input",
                tags=["python", "pickle", "user-input", "critical"]
            ),

            DetectorValidationSample(
                name="deserial_python_pickle_load_file",
                code='''
import pickle

def load_user_profile(filename):
    # VULNERABLE: pickle.load() from file
    with open(filename, 'rb') as f:
        profile = pickle.load(f)
    return profile
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="Deserialization via pickle.load() from file",
                tags=["python", "pickle", "file", "basic"]
            ),

            DetectorValidationSample(
                name="deserial_python_yaml_unsafe_load",
                code='''
import yaml

def parse_config(config_str):
    # VULNERABLE: yaml.load() without safe_load
    config = yaml.load(config_str)
    return config
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="Unsafe YAML deserialization with yaml.load()",
                tags=["python", "yaml", "unsafe-load"]
            ),

            DetectorValidationSample(
                name="deserial_python_yaml_fullloader",
                code='''
import yaml

def parse_settings(yaml_string):
    # VULNERABLE: yaml.load() with FullLoader still allows arbitrary objects
    settings = yaml.load(yaml_string, Loader=yaml.FullLoader)
    return settings
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="Unsafe YAML with FullLoader",
                tags=["python", "yaml", "fullloader"]
            ),

            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="deserial_python_json_loads_secure",
                code='''
import json
from flask import Flask, request

app = Flask(__name__)

@app.route('/data', methods=['POST'])
def process_data():
    json_data = request.data
    # SECURE: json.loads() is safe - only deserializes JSON primitives
    data = json.loads(json_data)
    return str(data)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure JSON deserialization",
                tags=["python", "json", "secure"]
            ),

            DetectorValidationSample(
                name="deserial_python_yaml_safe_load",
                code='''
import yaml

def parse_config(config_str):
    # SECURE: yaml.safe_load() prevents arbitrary code execution
    config = yaml.safe_load(config_str)
    return config
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure YAML deserialization with safe_load()",
                tags=["python", "yaml", "safe-load", "secure"]
            ),

            DetectorValidationSample(
                name="deserial_python_pickle_hmac_signed",
                code='''
import pickle
import hmac
import hashlib

SECRET_KEY = b'secret-key'

def load_signed_data(signed_data):
    # SECURE: HMAC signature verification before pickle.loads()
    signature = signed_data[:32]
    data = signed_data[32:]

    expected_sig = hmac.new(SECRET_KEY, data, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected_sig):
        raise ValueError("Invalid signature")

    return pickle.loads(data)
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure pickle with HMAC verification",
                tags=["python", "pickle", "hmac", "signed", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="deserial_javascript_eval",
                code='''
const express = require('express');
const app = express();

app.post('/data', (req, res) => {
    const data = req.body.data;
    // VULNERABLE: eval() can execute arbitrary code
    const obj = eval('(' + data + ')');
    res.send(obj);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="Code injection via eval()",
                tags=["javascript", "eval", "critical"]
            ),

            DetectorValidationSample(
                name="deserial_javascript_node_serialize",
                code='''
const serialize = require('node-serialize');
const express = require('express');

app.post('/deserialize', (req, res) => {
    const data = req.body.serialized;
    // VULNERABLE: node-serialize.unserialize() executes code
    const obj = serialize.unserialize(data);
    res.json(obj);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="Unsafe deserialization with node-serialize",
                tags=["javascript", "node-serialize", "basic"]
            ),

            DetectorValidationSample(
                name="deserial_javascript_function_constructor",
                code='''
const express = require('express');
const app = express();

app.post('/process', (req, res) => {
    // VULNERABLE: Function() constructor with user input
    const func = new Function('return ' + req.body.code);
    res.send(func());
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="Code injection via Function() constructor",
                tags=["javascript", "function-constructor", "advanced"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="deserial_javascript_json_parse_secure",
                code='''
const express = require('express');
const app = express();

app.post('/data', (req, res) => {
    const jsonString = req.body.data;
    // SECURE: JSON.parse() is safe - only parses JSON
    const obj = JSON.parse(jsonString);
    res.json(obj);
});
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure JSON.parse() deserialization",
                tags=["javascript", "json-parse", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - Java ==========

            DetectorValidationSample(
                name="deserial_java_objectinputstream",
                code='''
import java.io.*;

public class DataLoader {
    public Object loadData(InputStream input) throws Exception {
        // VULNERABLE: ObjectInputStream deserializes arbitrary objects
        ObjectInputStream ois = new ObjectInputStream(input);
        Object obj = ois.readObject();
        return obj;
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="Unsafe Java deserialization with ObjectInputStream",
                tags=["java", "objectinputstream", "basic"]
            ),

            DetectorValidationSample(
                name="deserial_java_xmldecoder",
                code='''
import java.beans.XMLDecoder;
import java.io.*;

public class ConfigLoader {
    public Object loadConfig(InputStream xmlInput) {
        // VULNERABLE: XMLDecoder can execute arbitrary code
        XMLDecoder decoder = new XMLDecoder(xmlInput);
        Object config = decoder.readObject();
        decoder.close();
        return config;
    }
}
''',
                language="java",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="Unsafe Java XMLDecoder deserialization",
                tags=["java", "xmldecoder", "advanced"]
            ),

            # ========== SECURE SAMPLES - Java ==========

            DetectorValidationSample(
                name="deserial_java_json_jackson",
                code='''
import com.fasterxml.jackson.databind.ObjectMapper;

public class DataProcessor {
    public MyData processData(String jsonString) throws Exception {
        // SECURE: Jackson JSON deserialization to specific type
        ObjectMapper mapper = new ObjectMapper();
        MyData data = mapper.readValue(jsonString, MyData.class);
        return data;
    }
}
''',
                language="java",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure Jackson JSON deserialization",
                tags=["java", "jackson", "json", "secure"]
            ),

            # ========== EDGE CASES ==========

            DetectorValidationSample(
                name="deserial_python_pickle_hardcoded",
                code='''
import pickle

def load_static_config():
    # MEDIUM RISK: pickle on trusted data, but still risky
    config_bytes = b'\\x80\\x03}q\\x00.'
    config = pickle.loads(config_bytes)
    return config
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["INSECURE_DESERIALIZATION"],
                expected_score=(0, 2),
                description="Pickle with hardcoded data (still flagged)",
                tags=["python", "pickle", "hardcoded", "edge-case"]
            ),

            DetectorValidationSample(
                name="deserial_python_ast_literal_eval",
                code='''
import ast

def parse_data(data_str):
    # SECURE: ast.literal_eval() only evaluates literals
    data = ast.literal_eval(data_str)
    return data
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure ast.literal_eval() for Python literals",
                tags=["python", "ast", "literal-eval", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDeserializationDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All Deserialization detector validation tests PASSED")
        print("The DeserializationDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} Deserialization detector validation tests FAILED")
        print("The DeserializationDetector has accuracy issues that must be fixed.")
        sys.exit(1)
