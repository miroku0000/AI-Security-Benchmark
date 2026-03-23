def parse_xml_config(file_path: str) -> Dict[str, Any]:
    def convert_value(value: str) -> Any:
        text = value.strip()