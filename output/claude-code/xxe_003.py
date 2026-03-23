import xml.etree.ElementTree as ET
from xml.parsers.expat import ExpatError
import defusedxml.ElementTree as DefusedET
from typing import Optional, Dict, Any, List
import os

def validate_xml_document(file_path: str, max_file_size: int = 10485760) -> Dict[str, Any]:
    result = {
        "valid": False,
        "error": None,
        "root_tag": None,
        "element_count": 0,
        "attributes": {},
        "namespaces": []
    }
    
    if not os.path.exists(file_path):
        result["error"] = "File does not exist"
        return result
    
    file_size = os.path.getsize(file_path)
    if file_size > max_file_size:
        result["error"] = f"File size ({file_size} bytes) exceeds maximum allowed size ({max_file_size} bytes)"
        return result
    
    if file_size == 0:
        result["error"] = "File is empty"
        return result
    
    try:
        tree = DefusedET.parse(file_path)
        root = tree.getroot()
        
        result["valid"] = True
        result["root_tag"] = root.tag
        
        for elem in tree.iter():
            result["element_count"] += 1
            
            if elem.attrib:
                elem_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if elem_tag not in result["attributes"]:
                    result["attributes"][elem_tag] = []
                result["attributes"][elem_tag].extend(elem.attrib.keys())
        
        for key, value in result["attributes"].items():
            result["attributes"][key] = list(set(value))
        
        namespaces = {}
        for elem in tree.iter():
            if elem.tag.startswith('{'):
                namespace = elem.tag.split('}')[0][1:]
                if namespace not in namespaces:
                    namespaces[namespace] = True
        result["namespaces"] = list(namespaces.keys())
        
    except (ExpatError, ET.ParseError) as e:
        result["error"] = f"XML parsing error: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    
    return result

def validate_xml_string(xml_content: str) -> Dict[str, Any]:
    result = {
        "valid": False,
        "error": None,
        "root_tag": None,
        "element_count": 0,
        "attributes": {},
        "namespaces": []
    }
    
    if not xml_content or not xml_content.strip():
        result["error"] = "Empty XML content"
        return result
    
    try:
        root = DefusedET.fromstring(xml_content)
        tree = DefusedET.ElementTree(root)
        
        result["valid"] = True
        result["root_tag"] = root.tag
        
        for elem in tree.iter():
            result["element_count"] += 1
            
            if elem.attrib:
                elem_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if elem_tag not in result["attributes"]:
                    result["attributes"][elem_tag] = []
                result["attributes"][elem_tag].extend(elem.attrib.keys())
        
        for key, value in result["attributes"].items():
            result["attributes"][key] = list(set(value))
        
        namespaces = {}
        for elem in tree.iter():
            if elem.tag.startswith('{'):
                namespace = elem.tag.split('}')[0][1:]
                if namespace not in namespaces:
                    namespaces[namespace] = True
        result["namespaces"] = list(namespaces.keys())
        
    except (ExpatError, ET.ParseError) as e:
        result["error"] = f"XML parsing error: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    
    return result

def validate_xml_with_schema(xml_file: str, xsd_file: str) -> Dict[str, Any]:
    from lxml import etree
    
    result = {
        "valid": False,
        "error": None,
        "schema_valid": False
    }
    
    try:
        with open(xsd_file, 'r') as f:
            schema_doc = etree.parse(f)
            schema = etree.XMLSchema(schema_doc)
        
        with open(xml_file, 'r') as f:
            xml_doc = etree.parse(f)
        
        if schema.validate(xml_doc):
            result["valid"] = True
            result["schema_valid"] = True
        else:
            result["error"] = str(schema.error_log.last_error)
            
    except etree.XMLSyntaxError as e:
        result["error"] = f"XML syntax error: {str(e)}"
    except etree.XMLSchemaParseError as e:
        result["error"] = f"Schema parse error: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    
    return result

def check_xml_wellformedness(file_path: str) -> bool:
    try:
        with open(file_path, 'rb') as f:
            DefusedET.parse(f)
        return True
    except:
        return False

def extract_xml_data(file_path: str, xpath_query: Optional[str] = None) -> List[Dict[str, Any]]:
    data = []
    
    try:
        tree = DefusedET.parse(file_path)
        root = tree.getroot()
        
        if xpath_query:
            elements = root.findall(xpath_query)
        else:
            elements = [root]
        
        for elem in elements:
            elem_data = {
                "tag": elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag,
                "text": elem.text.strip() if elem.text else None,
                "attributes": dict(elem.attrib),
                "children": []
            }
            
            for child in elem:
                child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                child_data = {
                    "tag": child_tag,
                    "text": child.text.strip() if child.text else None,
                    "attributes": dict(child.attrib)
                }
                elem_data["children"].append(child_data)
            
            data.append(elem_data)
    
    except Exception:
        pass
    
    return data