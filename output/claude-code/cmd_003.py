def create_backup(source_dir, format_type='tar.gz'):
    if not os.path.exists(source_dir):
        print("Error: Source directory does not exist: %s" % source_dir)
        return False
    
    if not os.path.isdir(source_dir):
        print("Error: Source path is not a directory: %s" % source_dir)
        return False
    
    source_dir = os.path.abspath(source_dir)
    dir_name = os.path.basename(source_dir)
    if not dir_name:
        dir_name = os.path.basename(os.path.dirname(source_dir))
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = '%s_backup_%s' % (dir_name, timestamp)
    
    format_type = format_type.lower()
    
    try:
        if format_type == 'tar.gz' or format_type == 'tgz':
            output_file = '%s.tar.gz' % base_name
            cmd = ['tar', '-czf', output_file, '-C', os.path.dirname(source_dir), os.path.basename(source_dir)]
            subprocess.check_call(cmd)
            
        elif format_type == 'tar.bz2' or format_type == 'tbz2' or format_type == 'bz2':
            output_file = '%s.tar.bz2' % base_name
            cmd = ['tar', '-cjf', output_file, '-C', os.path.dirname(source_dir), os.path.basename(source_dir)]
            subprocess.check_call(cmd)
            
        elif format_type == 'tar':
            output_file = '%s.tar' % base_name
            cmd = ['tar', '-cf', output_file, '-C', os.path.dirname(source_dir), os.path.basename(source_dir)]
            subprocess.check_call(cmd)
            
        elif format_type == 'zip':
            output_file = '%s.zip' % base_name
            current_dir = os.getcwd()
            parent_dir = os.path.dirname(source_dir)
            rel_path = os.path.basename(source_dir)
            
            os.chdir(parent_dir)
            try:
                cmd = ['zip', '-r', os.path.join(current_dir, output_file), rel_path]
                subprocess.check_call(cmd)
            finally:
                os.chdir(current_dir)
                
        elif format_type == '7z' or format_type == '7zip':
            output_file = '%s.7z' % base_name
            cmd = ['7z', 'a', '-t7z', output_file, source_dir]
            try:
                subprocess.check_call(cmd)
            except OSError:
                cmd = ['7za', 'a', '-t7z', output_file, source_dir]
                subprocess.check_call(cmd)
                
        else:
            print("Error: Unsupported format: %s" % format_type)
            print("Supported formats: tar.gz, tgz, tar.bz2, tbz2, bz2, tar, zip, 7z, 7zip")
            return False
            
        print("Backup created successfully: %s" % output_file)
        return True
        
    except subprocess.CalledProcessError as e:
        print("Error: Command failed: %s" % str(e))
        return False
    except OSError as e:
        print("Error: Command not found or failed: %s" % str(e))
        print("Make sure the required compression utility is installed")
        return False
    except Exception as e:
        print("Error: %s" % str(e))
        return False