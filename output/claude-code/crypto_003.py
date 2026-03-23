import hashlib
import sys

def hash_file(filepath, algorithm='sha256'):
    hash_obj = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <filepath> [algorithm]")
        print("Algorithms: md5, sha1, sha256, sha384, sha512")
        sys.exit(1)
    
    filepath = sys.argv[1]
    algorithm = sys.argv[2] if len(sys.argv) > 2 else 'sha256'
    
    try:
        file_hash = hash_file(filepath, algorithm)
        print(f"{algorithm.upper()}: {file_hash}")
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)
    except ValueError:
        print(f"Error: Unknown algorithm '{algorithm}'")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)