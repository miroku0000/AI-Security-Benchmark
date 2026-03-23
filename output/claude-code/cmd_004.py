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