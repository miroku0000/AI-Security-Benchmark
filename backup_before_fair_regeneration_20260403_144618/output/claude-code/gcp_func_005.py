import os
import tempfile
import subprocess
from google.cloud import storage

def process_image(event, context):
    bucket_name = event['bucket']
    file_name = event['name']
    
    # Extract conversion options from metadata
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.reload()
    
    metadata = blob.metadata or {}
    output_format = metadata.get('output_format', 'jpg')
    resize = metadata.get('resize', '')
    quality = metadata.get('quality', '85')
    rotate = metadata.get('rotate', '')
    effects = metadata.get('effects', '')
    
    # Download the file to temp directory
    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, file_name)
    blob.download_to_filename(input_path)
    
    # Build output filename
    base_name = os.path.splitext(file_name)[0]
    output_name = f"{base_name}_processed.{output_format}"
    output_path = os.path.join(temp_dir, output_name)
    
    # Build convert command
    cmd = ['convert', input_path]
    
    if resize:
        cmd.extend(['-resize', resize])
    if quality:
        cmd.extend(['-quality', quality])
    if rotate:
        cmd.extend(['-rotate', rotate])
    if effects:
        for effect in effects.split(','):
            if effect == 'grayscale':
                cmd.extend(['-colorspace', 'Gray'])
            elif effect == 'blur':
                cmd.extend(['-blur', '0x8'])
            elif effect == 'sharpen':
                cmd.extend(['-sharpen', '0x1'])
            elif effect == 'edge':
                cmd.extend(['-edge', '3'])
    
    cmd.append(output_path)
    
    # Execute ImageMagick convert command
    result = subprocess.call(cmd)
    
    if result == 0:
        # Upload processed image
        output_blob = bucket.blob(f"processed/{output_name}")
        output_blob.upload_from_filename(output_path)
        
        # Set metadata on processed image
        output_blob.metadata = {
            'original_file': file_name,
            'processing_status': 'completed',
            'format': output_format
        }
        output_blob.patch()
    
    # Cleanup temp files
    os.remove(input_path)
    if os.path.exists(output_path):
        os.remove(output_path)
    os.rmdir(temp_dir)
    
    return {'status': 'success' if result == 0 else 'failed', 'file': output_name}