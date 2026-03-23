from lxml import etree
import io

def process_soap_request(xml_data):
    parser = etree.XMLParser(
        dtd_validation=True,
        no_network=False,
        load_dtd=True,
        resolve_entities=True
    )
    
    try:
        if isinstance(xml_data, str):
            xml_data = xml_data.encode('utf-8')
        
        tree = etree.parse(io.BytesIO(xml_data), parser)
        root = tree.getroot()
        
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'soap12': 'http://www.w3.org/2003/05/soap-envelope'
        }
        
        body = root.find('.//soap:Body', namespaces)
        if body is None:
            body = root.find('.//soap12:Body', namespaces)
        
        if body is not None and len(body) > 0:
            message_element = body[0]
            
            result = {
                'tag': message_element.tag,
                'text': message_element.text,
                'attributes': dict(message_element.attrib),
                'children': []
            }
            
            for child in message_element:
                child_data = {
                    'tag': child.tag,
                    'text': child.text,
                    'attributes': dict(child.attrib)
                }
                result['children'].append(child_data)
            
            return result
        
        return None
        
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML: {e}")
    except Exception as e:
        raise Exception(f"Error processing SOAP request: {e}")

def validate_with_dtd(xml_data, dtd_string):
    dtd = etree.DTD(io.StringIO(dtd_string))
    
    parser = etree.XMLParser(
        dtd_validation=True,
        load_dtd=True,
        resolve_entities=True
    )
    
    if isinstance(xml_data, str):
        xml_data = xml_data.encode('utf-8')
    
    doc = etree.parse(io.BytesIO(xml_data), parser)
    
    if dtd.validate(doc):
        return True
    else:
        raise ValueError(f"DTD validation failed: {dtd.error_log}")

def extract_soap_action(xml_data):
    parser = etree.XMLParser(
        dtd_validation=True,
        load_dtd=True,
        resolve_entities=True
    )
    
    if isinstance(xml_data, str):
        xml_data = xml_data.encode('utf-8')
    
    tree = etree.parse(io.BytesIO(xml_data), parser)
    root = tree.getroot()
    
    namespaces = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'soap12': 'http://www.w3.org/2003/05/soap-envelope'
    }
    
    header = root.find('.//soap:Header', namespaces)
    if header is None:
        header = root.find('.//soap12:Header', namespaces)
    
    if header is not None:
        action = header.find('.//{http://www.w3.org/2005/08/addressing}Action')
        if action is not None:
            return action.text
    
    return None

def parse_soap_fault(xml_data):
    parser = etree.XMLParser(
        dtd_validation=True,
        load_dtd=True,
        resolve_entities=True
    )
    
    if isinstance(xml_data, str):
        xml_data = xml_data.encode('utf-8')
    
    tree = etree.parse(io.BytesIO(xml_data), parser)
    root = tree.getroot()
    
    namespaces = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'soap12': 'http://www.w3.org/2003/05/soap-envelope'
    }
    
    fault = root.find('.//soap:Fault', namespaces)
    if fault is None:
        fault = root.find('.//soap12:Fault', namespaces)
    
    if fault is not None:
        fault_data = {}
        
        faultcode = fault.find('.//faultcode')
        if faultcode is not None:
            fault_data['code'] = faultcode.text
        
        faultstring = fault.find('.//faultstring')
        if faultstring is not None:
            fault_data['string'] = faultstring.text
        
        faultactor = fault.find('.//faultactor')
        if faultactor is not None:
            fault_data['actor'] = faultactor.text
        
        detail = fault.find('.//detail')
        if detail is not None:
            fault_data['detail'] = etree.tostring(detail, encoding='unicode')
        
        return fault_data
    
    return None