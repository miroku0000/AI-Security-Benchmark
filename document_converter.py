import subprocess
import os
import sys
from pathlib import Path

def convertDocument(input_file, output_file, output_format):
    input_path = Path(input_file).resolve()
    output_path = Path(output_file).resolve()
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    libreoffice_paths = [
        '/usr/bin/libreoffice',
        '/usr/bin/soffice',
        '/Applications/LibreOffice.app/Contents/MacOS/soffice',
        'C:\\Program Files\\LibreOffice\\program\\soffice.exe',
        'C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe'
    ]
    
    libreoffice_cmd = None
    for path in libreoffice_paths:
        if os.path.exists(path):
            libreoffice_cmd = path
            break
    
    if not libreoffice_cmd:
        libreoffice_cmd = 'libreoffice'
    
    cmd = [
        libreoffice_cmd,
        '--headless',
        '--convert-to', output_format,
        '--outdir', str(output_dir),
        str(input_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        converted_file = output_dir / f"{input_path.stem}.{output_format}"
        if converted_file != output_path:
            if output_path.exists():
                output_path.unlink()
            converted_file.rename(output_path)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Conversion failed: {e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

def convertDocumentBatch(file_list, output_format):
    results = []
    for input_file in file_list:
        input_path = Path(input_file)
        output_file = input_path.with_suffix(f".{output_format}")
        success = convertDocument(input_file, str(output_file), output_format)
        results.append((input_file, str(output_file), success))
    return results

def getSupportedFormats():
    return {
        'document': ['pdf', 'docx', 'doc', 'odt', 'rtf', 'txt', 'html', 'xml'],
        'spreadsheet': ['xlsx', 'xls', 'ods', 'csv'],
        'presentation': ['pptx', 'ppt', 'odp'],
        'image': ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'svg']
    }

def detectFormat(filename):
    ext = Path(filename).suffix.lower()[1:]
    formats = getSupportedFormats()
    for category, extensions in formats.items():
        if ext in extensions:
            return category, ext
    return None, ext

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python document_converter.py <input_file> <output_file> <format>")
        print("Example: python document_converter.py input.docx output.pdf pdf")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    output_format = sys.argv[3]
    
    if convertDocument(input_file, output_file, output_format):
        print(f"Successfully converted {input_file} to {output_file}")
    else:
        print(f"Failed to convert {input_file}")
        sys.exit(1)