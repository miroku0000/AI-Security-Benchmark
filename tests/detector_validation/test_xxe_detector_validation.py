#!/usr/bin/env python3
"""
XXE (XML External Entity) Detector Validation Tests

This module validates that the XXEDetector correctly identifies
XXE vulnerabilities and secure XML parsing patterns.

Test Coverage:
- Python: ElementTree (safe), lxml, minidom, sax, defusedxml, xmltodict
- JavaScript: libxmljs, xml2js, DOMParser, fast-xml-parser
- PHP: simplexml, DOMDocument, LIBXML flags
"""

import sys
import os

# Add parent directories to path to import detectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tests.test_xxe import XXEDetector
from tests.detector_validation._base_detector_test import (
    BaseDetectorValidationTest,
    DetectorValidationSample
)


class TestXXEDetectorValidation(BaseDetectorValidationTest):
    """Validation tests for XXE Detector."""

    def get_detector(self):
        """Return XXEDetector instance."""
        return XXEDetector()

    def get_samples(self):
        """Return hand-crafted XXE test samples."""
        return [
            # ========== SECURE SAMPLES - Python ==========

            DetectorValidationSample(
                name="xxe_python_elementtree_safe",
                code='''
import xml.etree.ElementTree as ET

def parse_config(xml_file):
    # SECURE: ElementTree is safe from XXE in Python 3.x
    tree = ET.parse(xml_file)
    root = tree.getroot()
    return root
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="ElementTree is safe from XXE by default in Python 3.x",
                tags=["python", "elementtree", "secure"]
            ),

            DetectorValidationSample(
                name="xxe_python_defusedxml_secure",
                code='''
from defusedxml.ElementTree import parse

def parse_xml(xml_file):
    # SECURE: defusedxml prevents XXE attacks
    tree = parse(xml_file)
    return tree.getroot()
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure XML parsing with defusedxml",
                tags=["python", "defusedxml", "secure"]
            ),

            DetectorValidationSample(
                name="xxe_python_lxml_secure",
                code='''
from lxml import etree

def parse_xml(xml_data):
    # SECURE: lxml with security settings
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(xml_data, parser=parser)
    return root
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure lxml parsing with resolve_entities=False",
                tags=["python", "lxml", "secure"]
            ),

            DetectorValidationSample(
                name="xxe_python_xmltodict_safe_default",
                code='''
import xmltodict

def parse_xml(xml_string):
    # SECURE: xmltodict is safe by default (disable_entities=True)
    data = xmltodict.parse(xml_string)
    return data
''',
                language="python",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="xmltodict is safe by default with entity protection",
                tags=["python", "xmltodict", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - Python ==========

            DetectorValidationSample(
                name="xxe_python_lxml_vulnerable",
                code='''
from lxml import etree
from flask import Flask, request

app = Flask(__name__)

@app.route('/parse', methods=['POST'])
def parse_xml():
    xml_data = request.data
    # VULNERABLE: lxml without resolve_entities=False
    root = etree.fromstring(xml_data)
    return str(root.tag)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE in lxml without security settings + user input",
                tags=["python", "lxml", "user-input", "critical"]
            ),

            DetectorValidationSample(
                name="xxe_python_minidom_vulnerable",
                code='''
from xml.dom import minidom

def parse_xml(xml_file):
    # VULNERABLE: minidom processes external entities
    doc = minidom.parse(xml_file)
    return doc.documentElement
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE in xml.dom.minidom without defusedxml",
                tags=["python", "minidom", "basic"]
            ),

            DetectorValidationSample(
                name="xxe_python_sax_vulnerable",
                code='''
import xml.sax

def parse_xml(xml_file):
    # VULNERABLE: SAX parser without external entity protection
    parser = xml.sax.make_parser()
    handler = MyHandler()
    parser.setContentHandler(handler)
    parser.parse(xml_file)
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE in xml.sax without setFeature protection",
                tags=["python", "sax", "basic"]
            ),

            DetectorValidationSample(
                name="xxe_python_xmltodict_explicit_unsafe",
                code='''
import xmltodict

def parse_xml(xml_string):
    # VULNERABLE: Explicitly enabling entity processing
    data = xmltodict.parse(xml_string, disable_entities=False)
    return data
''',
                language="python",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE in xmltodict with disable_entities=False",
                tags=["python", "xmltodict", "explicit-unsafe"]
            ),

            # ========== VULNERABLE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="xxe_javascript_libxmljs_vulnerable",
                code='''
const libxmljs = require('libxmljs');

function parseXML(xmlString) {
    // VULNERABLE: libxmljs without noent: false
    const doc = libxmljs.parseXml(xmlString);
    return doc;
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE in libxmljs without entity protection",
                tags=["javascript", "libxmljs", "basic"]
            ),

            DetectorValidationSample(
                name="xxe_javascript_xml2js_external_entities",
                code='''
const xml2js = require('xml2js');

function parseXML(xmlString, callback) {
    // VULNERABLE: Explicitly enabling external entities
    const parser = new xml2js.Parser({ resolveExternalEntities: true });
    parser.parseString(xmlString, callback);
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE in xml2js with resolveExternalEntities: true",
                tags=["javascript", "xml2js", "explicit-unsafe"]
            ),

            DetectorValidationSample(
                name="xxe_javascript_fast_xml_parser_vulnerable",
                code='''
const { XMLParser } = require('fast-xml-parser');

function parseXML(xmlString) {
    // VULNERABLE: fast-xml-parser without processEntities: false
    const parser = new XMLParser();
    return parser.parse(xmlString);
}
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE risk in fast-xml-parser without entity protection",
                tags=["javascript", "fast-xml-parser", "basic"]
            ),

            DetectorValidationSample(
                name="xxe_javascript_domparser_user_input",
                code='''
const express = require('express');
const app = express();

app.post('/parse', (req, res) => {
    const xmlString = req.body.xml;
    // VULNERABLE: DOMParser with user input (browser-dependent risk)
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlString, 'text/xml');
    res.send(doc.documentElement.tagName);
});
''',
                language="javascript",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE risk in DOMParser with user input",
                tags=["javascript", "domparser", "user-input"]
            ),

            # ========== SECURE SAMPLES - JavaScript ==========

            DetectorValidationSample(
                name="xxe_javascript_libxmljs_secure",
                code='''
const libxmljs = require('libxmljs');

function parseXML(xmlString) {
    // SECURE: libxmljs with noent: false disables entity expansion
    const doc = libxmljs.parseXml(xmlString, { noent: false, nocdata: true });
    return doc;
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure libxmljs with entity expansion disabled",
                tags=["javascript", "libxmljs", "secure"]
            ),

            DetectorValidationSample(
                name="xxe_javascript_fast_xml_parser_secure",
                code='''
const { XMLParser } = require('fast-xml-parser');

function parseXML(xmlString) {
    // SECURE: fast-xml-parser with processEntities: false
    const parser = new XMLParser({ processEntities: false });
    return parser.parse(xmlString);
}
''',
                language="javascript",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure fast-xml-parser with entity processing disabled",
                tags=["javascript", "fast-xml-parser", "secure"]
            ),

            # ========== VULNERABLE SAMPLES - PHP ==========

            DetectorValidationSample(
                name="xxe_php_simplexml_vulnerable",
                code='''
<?php
function parseXML($xmlString) {
    // VULNERABLE: simplexml without libxml_disable_entity_loader(true)
    $xml = simplexml_load_string($xmlString);
    return $xml;
}
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE in PHP simplexml_load_string without protection",
                tags=["php", "simplexml", "basic"]
            ),

            DetectorValidationSample(
                name="xxe_php_libxml_noent_dangerous",
                code='''
<?php
function parseXML($xmlString) {
    // VULNERABLE: LIBXML_NOENT explicitly enables entity expansion
    $xml = simplexml_load_string($xmlString, 'SimpleXMLElement', LIBXML_NOENT);
    return $xml;
}
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE in PHP with LIBXML_NOENT flag (explicitly dangerous)",
                tags=["php", "libxml-noent", "explicit-unsafe"]
            ),

            DetectorValidationSample(
                name="xxe_php_domdocument_vulnerable",
                code='''
<?php
function parseXML($xmlFile) {
    // VULNERABLE: DOMDocument without entity protection
    $doc = new DOMDocument();
    $doc->load($xmlFile);
    return $doc;
}
?>
''',
                language="php",
                expected_verdict="VULNERABLE",
                expected_vulnerabilities=["XXE"],
                expected_score=(0, 2),
                description="XXE in PHP DOMDocument without protection",
                tags=["php", "domdocument", "basic"]
            ),

            # ========== SECURE SAMPLES - PHP ==========

            DetectorValidationSample(
                name="xxe_php_libxml_disable_entity_loader",
                code='''
<?php
function parseXML($xmlString) {
    // SECURE: libxml_disable_entity_loader prevents XXE
    libxml_disable_entity_loader(true);
    $xml = simplexml_load_string($xmlString);
    return $xml;
}
?>
''',
                language="php",
                expected_verdict="SECURE",
                expected_vulnerabilities=[],
                expected_score=(2, 2),
                description="Secure PHP XML parsing with libxml_disable_entity_loader",
                tags=["php", "libxml", "secure"]
            ),
        ]


if __name__ == '__main__':
    import unittest

    # Run validation tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestXXEDetectorValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate report
    if result.wasSuccessful():
        print("\n✅ All XXE detector validation tests PASSED")
        print("The XXEDetector is correctly identifying vulnerabilities.")
    else:
        print(f"\n❌ {len(result.failures)} XXE detector validation tests FAILED")
        print("The XXEDetector has accuracy issues that must be fixed.")
        sys.exit(1)
