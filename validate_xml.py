import xml.etree.ElementTree as ET
import xml.parsers.expat
import os
from typing import Optional, Dict, Any, Union
import re


def validate_xml_document(xml_input: Union[str, bytes], 
                         schema_file: Optional[str] = None,
                         max_size_bytes: int = 10485760,
                         allow_dtd: bool = False,
                         allow_entities: bool = False) -> Dict[str, Any]:
    
    result = {
        'valid': False,
        'errors': [],
        'warnings': [],
        'xml_version': None,
        'encoding': None,
        'root_element': None,
        'element_count': 0,
        'attribute_count': 0,
        'depth': 0,
        'namespaces': [],
        'dtd_detected': False,
        'entities_detected': False,
        'external_references': False,
        'size_bytes': 0
    }
    
    try:
        # Check if input is file path or XML string/bytes
        if isinstance(xml_input, str) and os.path.isfile(xml_input):
            with open(xml_input, 'rb') as f:
                xml_data = f.read()
                result['size_bytes'] = len(xml_data)
        elif isinstance(xml_input, bytes):
            xml_data = xml_input
            result['size_bytes'] = len(xml_data)
        else:
            xml_data = xml_input.encode('utf-8') if isinstance(xml_input, str) else xml_input
            result['size_bytes'] = len(xml_data)
        
        # Check file size
        if result['size_bytes'] > max_size_bytes:
            result['errors'].append(f"XML document exceeds maximum size limit ({max_size_bytes} bytes)")
            return result
            
        # Check for DTD declarations
        if b'<!DOCTYPE' in xml_data or b'<!ENTITY' in xml_data:
            result['dtd_detected'] = True
            if not allow_dtd:
                result['errors'].append("DTD declarations detected but not allowed")
                return result
                
        # Check for entity references
        entity_pattern = rb'&[^;]+;'
        standard_entities = [b'&lt;', b'&gt;', b'&amp;', b'&apos;', b'&quot;']
        entities_found = re.findall(entity_pattern, xml_data)
        custom_entities = [e for e in entities_found if e not in standard_entities]
        
        if custom_entities:
            result['entities_detected'] = True
            if not allow_entities:
                result['errors'].append(f"Custom entity references detected: {[e.decode('utf-8', errors='ignore') for e in custom_entities[:5]]}")
                return result
                
        # Check for external references
        if b'SYSTEM' in xml_data or b'PUBLIC' in xml_data:
            result['external_references'] = True
            result['warnings'].append("External references detected in XML")
            
        # Create secure parser
        parser = ET.XMLParser()
        parser.parser.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)
        
        # Parse XML
        try:
            if isinstance(xml_input, str) and os.path.isfile(xml_input):
                tree = ET.parse(xml_input, parser=parser)
                root = tree.getroot()
            else:
                root = ET.fromstring(xml_data, parser=parser)
                tree = ET.ElementTree(root)
        except ET.ParseError as e:
            result['errors'].append(f"XML parsing error: {str(e)}")
            return result
            
        # Extract XML declaration info if available
        if xml_data.startswith(b'<?xml'):
            decl_end = xml_data.find(b'?>')
            if decl_end > 0:
                decl = xml_data[:decl_end+2].decode('utf-8', errors='ignore')
                version_match = re.search(r'version=["\']([^"\']+)["\']', decl)
                encoding_match = re.search(r'encoding=["\']([^"\']+)["\']', decl)
                if version_match:
                    result['xml_version'] = version_match.group(1)
                if encoding_match:
                    result['encoding'] = encoding_match.group(1)
                    
        # Analyze document structure
        result['root_element'] = {
            'tag': root.tag,
            'attributes': dict(root.attrib),
            'text': (root.text or '').strip()[:100]
        }
        
        # Count elements and calculate depth
        def analyze_element(elem, depth=1):
            nonlocal result
            result['element_count'] += 1
            result['attribute_count'] += len(elem.attrib)
            result['depth'] = max(result['depth'], depth)
            
            # Check for namespaces
            if '}' in elem.tag:
                ns = elem.tag.split('}')[0][1:]
                if ns not in result['namespaces']:
                    result['namespaces'].append(ns)
                    
            for child in elem:
                analyze_element(child, depth + 1)
                
        for child in root:
            analyze_element(child)
            
        # Add root element to counts
        result['element_count'] += 1
        result['attribute_count'] += len(root.attrib)
        
        # Validate against XSD schema if provided
        if schema_file and os.path.isfile(schema_file):
            try:
                schema_doc = ET.parse(schema_file)
                schema_root = schema_doc.getroot()
                
                # Basic schema validation (simplified)
                if 'XMLSchema' in schema_root.tag:
                    result['warnings'].append("XSD schema validation requested but full validation not implemented")
                else:
                    result['warnings'].append(f"Schema file does not appear to be XSD: {schema_root.tag}")
            except Exception as e:
                result['warnings'].append(f"Could not load schema file: {str(e)}")
                
        # Check for common XML security issues
        if result['element_count'] > 10000:
            result['warnings'].append("Large number of elements detected (possible XML bomb)")
            
        if result['depth'] > 100:
            result['warnings'].append("Deep nesting detected (possible XML bomb)")
            
        # Check for CDATA sections
        if b'<![CDATA[' in xml_data:
            result['warnings'].append("CDATA sections detected in document")
            
        # Check for processing instructions
        if b'<?' in xml_data[50:]:  # Skip XML declaration
            result['warnings'].append("Processing instructions detected in document")
            
        # Document is valid if we got here
        result['valid'] = True
        
    except Exception as e:
        result['errors'].append(f"Unexpected error during validation: {str(e)}")
        
    return result


def validate_and_parse(xml_input: Union[str, bytes], 
                      safe_mode: bool = True) -> Optional[ET.Element]:
    
    validation = validate_xml_document(
        xml_input,
        allow_dtd=not safe_mode,
        allow_entities=not safe_mode
    )
    
    if not validation['valid']:
        print("XML Validation Failed:")
        for error in validation['errors']:
            print(f"  ERROR: {error}")
        for warning in validation['warnings']:
            print(f"  WARNING: {warning}")
        return None
        
    # Parse and return the root element
    parser = ET.XMLParser()
    if safe_mode:
        parser.parser.SetParamEntityParsing(xml.parsers.expat.XML_PARAM_ENTITY_PARSING_NEVER)
        
    try:
        if isinstance(xml_input, str) and os.path.isfile(xml_input):
            tree = ET.parse(xml_input, parser=parser)
            return tree.getroot()
        else:
            xml_data = xml_input if isinstance(xml_input, bytes) else xml_input.encode('utf-8')
            return ET.fromstring(xml_data, parser=parser)
    except Exception as e:
        print(f"Failed to parse XML: {e}")
        return None


if __name__ == "__main__":
    # Test with sample XML
    test_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <configuration>
        <database>
            <host>localhost</host>
            <port>5432</port>
            <name>myapp</name>
            <credentials>
                <username>appuser</username>
                <password>secret123</password>
            </credentials>
        </database>
        <logging>
            <level>INFO</level>
            <file>/var/log/app.log</file>
        </logging>
    </configuration>"""
    
    # Validate the XML
    result = validate_xml_document(test_xml)
    
    print("Validation Result:")
    print(f"  Valid: {result['valid']}")
    print(f"  XML Version: {result['xml_version']}")
    print(f"  Encoding: {result['encoding']}")
    print(f"  Root Element: {result['root_element']['tag']}")
    print(f"  Elements: {result['element_count']}")
    print(f"  Attributes: {result['attribute_count']}")
    print(f"  Max Depth: {result['depth']}")
    print(f"  Size: {result['size_bytes']} bytes")
    
    if result['errors']:
        print("  Errors:")
        for error in result['errors']:
            print(f"    - {error}")
            
    if result['warnings']:
        print("  Warnings:")
        for warning in result['warnings']:
            print(f"    - {warning}")
            
    # Parse the XML safely
    print("\nParsing XML...")
    root = validate_and_parse(test_xml)
    if root:
        print(f"Successfully parsed. Root tag: {root.tag}")
        
    # Test with malicious XML (XXE attempt)
    xxe_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE foo [
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
    ]>
    <data>&xxe;</data>"""
    
    print("\n\nTesting XXE prevention:")
    result = validate_xml_document(xxe_xml)
    print(f"  Valid: {result['valid']}")
    if result['errors']:
        print("  Errors:")
        for error in result['errors']:
            print(f"    - {error}")