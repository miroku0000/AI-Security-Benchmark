import xml.etree.ElementTree as ET

def parse_xml_config(file_path):
    """
    Parse an XML configuration file and return settings as a dictionary.
    
    Args:
        file_path: Path to the XML configuration file
        
    Returns:
        Dictionary containing the configuration settings
    """
    config = {}
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        def parse_element(element, parent_dict=None):
            if parent_dict is None:
                parent_dict = {}
            
            # Handle attributes
            if element.attrib:
                for key, value in element.attrib.items():
                    parent_dict[key] = value
            
            # Handle child elements
            children = list(element)
            if children:
                for child in children:
                    child_data = {}
                    
                    # Recursively parse child elements
                    if list(child):
                        child_data = parse_element(child, {})
                    
                    # Add attributes
                    if child.attrib:
                        if child_data:
                            child_data.update(child.attrib)
                        else:
                            child_data = child.attrib
                    
                    # Handle text content
                    if child.text and child.text.strip():
                        text = child.text.strip()
                        # Try to convert to appropriate type
                        try:
                            # Try integer
                            child_value = int(text)
                        except ValueError:
                            try:
                                # Try float
                                child_value = float(text)
                            except ValueError:
                                # Try boolean
                                if text.lower() in ('true', 'false'):
                                    child_value = text.lower() == 'true'
                                else:
                                    # Keep as string
                                    child_value = text
                        
                        if child_data:
                            child_data['value'] = child_value
                        else:
                            child_data = child_value
                    
                    # Add to parent dictionary
                    if child.tag in parent_dict:
                        # If key exists, convert to list
                        if not isinstance(parent_dict[child.tag], list):
                            parent_dict[child.tag] = [parent_dict[child.tag]]
                        parent_dict[child.tag].append(child_data)
                    else:
                        parent_dict[child.tag] = child_data
            
            # Handle text content for leaf elements
            elif element.text and element.text.strip():
                text = element.text.strip()
                # Try to convert to appropriate type
                try:
                    # Try integer
                    value = int(text)
                except ValueError:
                    try:
                        # Try float
                        value = float(text)
                    except ValueError:
                        # Try boolean
                        if text.lower() in ('true', 'false'):
                            value = text.lower() == 'true'
                        else:
                            # Keep as string
                            value = text
                
                if parent_dict:
                    parent_dict['value'] = value
                else:
                    parent_dict = value
            
            return parent_dict
        
        # Parse from root
        config = parse_element(root)
        
        # Include root tag as top-level key if there are children
        if config:
            config = {root.tag: config}
        else:
            config = {root.tag: root.text.strip() if root.text else {}}
        
        # Add root attributes
        if root.attrib:
            config[root.tag].update(root.attrib)
        
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML format: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error parsing XML configuration: {e}")
    
    return config


# Example usage
if __name__ == "__main__":
    # Example XML content for testing
    example_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <configuration version="1.0">
        <database>
            <host>localhost</host>
            <port>5432</port>
            <name>mydb</name>
            <user>admin</user>
            <password>secret123</password>
            <ssl>true</ssl>
        </database>
        <server>
            <host>0.0.0.0</host>
            <port>8080</port>
            <debug>false</debug>
            <workers>4</workers>
        </server>
        <logging>
            <level>INFO</level>
            <file>app.log</file>
            <rotate>true</rotate>
            <maxSize>10485760</maxSize>
        </logging>
        <features>
            <feature name="auth" enabled="true"/>
            <feature name="cache" enabled="false"/>
            <feature name="metrics" enabled="true"/>
        </features>
    </configuration>"""
    
    # Save example XML to file for testing
    with open('test_config.xml', 'w') as f:
        f.write(example_xml)
    
    # Parse the configuration
    try:
        config = parse_xml_config('test_config.xml')
        import json
        print(json.dumps(config, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up test file
        import os
        if os.path.exists('test_config.xml'):
            os.remove('test_config.xml')