from flask import Flask, request, jsonify
from lxml import etree
import io

app = Flask(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024

def validate_xml(xml_content):
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
        huge_tree=False
    )
    
    try:
        etree.fromstring(xml_content.encode('utf-8'), parser=parser)
        return True, "Valid XML"
    except etree.XMLSyntaxError as e:
        return False, f"XML syntax error: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

@app.route('/upload-xml', methods=['POST'])
def upload_xml():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.xml'):
        return jsonify({'error': 'File must be XML'}), 400
    
    content = file.read()
    
    if len(content) > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large'}), 400
    
    xml_content = content.decode('utf-8')
    is_valid, message = validate_xml(xml_content)
    
    if is_valid:
        return jsonify({'status': 'success', 'message': message}), 200
    else:
        return jsonify({'status': 'error', 'message': message}), 400

if __name__ == '__main__':
    app.run(debug=False)