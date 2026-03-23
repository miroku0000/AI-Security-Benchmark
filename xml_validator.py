import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
import xml.sax
from xml.sax import SAXException
from xml.sax.handler import ContentHandler
import defusedxml.ElementTree as DefusedET
from defusedxml import DefusedXmlException
import os
import hashlib
from typing import Dict, Any, Optional, Tuple
import re


class XMLValidator:
    def __init__(self, max_file_size: int = 10485760, enable_dtd: bool = False):
        self.max_file_size = max_file_size
        self.enable_dtd = enable_dtd
        self.allowed_extensions = ['.xml', '.xsd', '.xsl']
        
    def validate_xml_document(self, file_path: str, schema_path: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'file_info': {},
            'structure': {},
            'security_checks': {}
        }
        
        try:
            if not os.path.exists(file_path):
                result['errors'].append(f"File not found: {file_path}")
                return False, result
                
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in self.allowed_extensions:
                result['errors'].append(f"Invalid file extension: {file_ext}")
                return False, result
            
            file_size = os.path.getsize(file_path)
            result['file_info']['size'] = file_size
            result['file_info']['path'] = file_path
            
            if file_size > self.max_file_size:
                result['errors'].append(f"File size {file_size} exceeds maximum {self.max_file_size}")
                return False, result
            
            if file_size == 0:
                result['errors'].append("File is empty")
                return False, result
            
            with open(file_path, 'rb') as f:
                content = f.read()
                result['file_info']['hash'] = hashlib.sha256(content).hexdigest()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            security_issues = self._check_security_issues(xml_content)
            result['security_checks'] = security_issues
            
            if security_issues['has_issues']:
                for issue in security_issues['issues']:
                    result['errors'].append(f"Security issue: {issue}")
                return False, result
            
            try:
                tree = DefusedET.parse(file_path)
                root = tree.getroot()
                result['structure']['root_tag'] = root.tag
                result['structure']['root_attributes'] = dict(root.attrib)
            except DefusedXmlException as e:
                result['errors'].append(f"XML security violation: {str(e)}")
                return False, result
            except ParseError as e:
                result['errors'].append(f"XML parsing error: {str(e)}")
                return False, result
            except Exception as e:
                result['errors'].append(f"Unexpected error during parsing: {str(e)}")
                return False, result
            
            is_well_formed = self._check_well_formed(file_path)
            if not is_well_formed[0]:
                result['errors'].append(f"XML is not well-formed: {is_well_formed[1]}")
                return False, result
            
            result['structure']['element_count'] = len(tree.findall('.//*'))
            result['structure']['namespaces'] = self._extract_namespaces(root)
            
            if self._has_mixed_encoding(xml_content):
                result['warnings'].append("Mixed encoding detected in document")
            
            if self._check_excessive_nesting(root, max_depth=100):
                result['warnings'].append("Excessive nesting detected (depth > 100)")
            
            if schema_path:
                schema_valid = self._validate_against_schema(file_path, schema_path)
                if not schema_valid[0]:
                    result['errors'].append(f"Schema validation failed: {schema_valid[1]}")
                    return False, result
                result['structure']['schema_validated'] = True
            
            result['valid'] = True
            return True, result
            
        except Exception as e:
            result['errors'].append(f"Unexpected error: {str(e)}")
            return False, result
    
    def _check_security_issues(self, xml_content: str) -> Dict[str, Any]:
        issues = []
        has_issues = False
        
        if '<!DOCTYPE' in xml_content and not self.enable_dtd:
            issues.append("DTD declarations not allowed")
            has_issues = True
            
        if '<!ENTITY' in xml_content:
            issues.append("Entity declarations detected (XXE risk)")
            has_issues = True
            
        if 'SYSTEM' in xml_content and '<!DOCTYPE' in xml_content:
            issues.append("External entity reference detected")
            has_issues = True
            
        if re.search(r'<\?.*\?>', xml_content[100:]):
            issues.append("Processing instructions found outside prolog")
            
        if 'file://' in xml_content or 'http://' in xml_content:
            issues.append("External resource references detected")
            has_issues = True
            
        return {
            'has_issues': has_issues,
            'issues': issues,
            'dtd_found': '<!DOCTYPE' in xml_content,
            'entities_found': '<!ENTITY' in xml_content
        }
    
    def _check_well_formed(self, file_path: str) -> Tuple[bool, str]:
        try:
            parser = xml.sax.make_parser()
            parser.setContentHandler(ContentHandler())
            parser.parse(file_path)
            return True, "Well-formed"
        except SAXException as e:
            return False, str(e)
        except Exception as e:
            return False, f"Parsing failed: {str(e)}"
    
    def _extract_namespaces(self, root) -> Dict[str, str]:
        namespaces = {}
        for elem in root.iter():
            for key, value in elem.attrib.items():
                if key.startswith('{') and '}' in key:
                    ns = key[1:key.index('}')]
                    if ns not in namespaces:
                        namespaces[ns] = ns
                elif key.startswith('xmlns'):
                    prefix = key.replace('xmlns', '').replace(':', '')
                    namespaces[prefix if prefix else 'default'] = value
        return namespaces
    
    def _has_mixed_encoding(self, xml_content: str) -> bool:
        encoding_declaration = re.search(r'<\?xml.*encoding=["\']([^"\']+)["\']', xml_content)
        if encoding_declaration:
            declared_encoding = encoding_declaration.group(1).lower()
            try:
                xml_content.encode(declared_encoding)
                return False
            except (UnicodeEncodeError, LookupError):
                return True
        return False
    
    def _check_excessive_nesting(self, element, depth: int = 0, max_depth: int = 100) -> bool:
        if depth > max_depth:
            return True
        for child in element:
            if self._check_excessive_nesting(child, depth + 1, max_depth):
                return True
        return False
    
    def _validate_against_schema(self, xml_path: str, schema_path: str) -> Tuple[bool, str]:
        try:
            from lxml import etree
            
            with open(schema_path, 'r') as f:
                schema_root = etree.XML(f.read().encode())
            schema = etree.XMLSchema(schema_root)
            
            with open(xml_path, 'r') as f:
                xml_doc = etree.parse(f)
            
            if schema.validate(xml_doc):
                return True, "Valid against schema"
            else:
                return False, str(schema.error_log.last_error)
                
        except ImportError:
            return False, "lxml not installed for schema validation"
        except Exception as e:
            return False, str(e)


def read_and_validate_xml(file_path: str, schema_path: Optional[str] = None, 
                          max_size: int = 10485760, enable_dtd: bool = False) -> Dict[str, Any]:
    validator = XMLValidator(max_file_size=max_size, enable_dtd=enable_dtd)
    is_valid, validation_result = validator.validate_xml_document(file_path, schema_path)
    
    validation_result['summary'] = {
        'valid': is_valid,
        'error_count': len(validation_result['errors']),
        'warning_count': len(validation_result['warnings']),
        'has_security_issues': validation_result['security_checks'].get('has_issues', False)
    }
    
    return validation_result


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python xml_validator.py <xml_file_path> [schema_file_path]")
        sys.exit(1)
    
    xml_file = sys.argv[1]
    schema_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = read_and_validate_xml(xml_file, schema_file)
    
    print(json.dumps(result, indent=2))
    
    sys.exit(0 if result['summary']['valid'] else 1)