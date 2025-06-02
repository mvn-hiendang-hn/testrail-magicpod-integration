#!/usr/bin/env python3
import os
import requests
import zipfile
import tempfile
from pathlib import Path

def download_magicpod_client():
    """Download and extract MagicPod API client"""
    
    # Check if API token is set
    api_token = os.getenv('MAGICPOD_API_TOKEN')
    if not api_token:
        raise ValueError("MAGICPOD_API_TOKEN environment variable is not set")
    
    print("Downloading MagicPod API client...")
    
    # Prepare headers
    headers = {
        'Authorization': f'Token {api_token}',
        'Accept': 'application/zip',
        'User-Agent': 'MagicPod-GitHub-Action/1.0'
    }
    
    try:
        # Download the ZIP file
        response = requests.get(
            'https://app.magicpod.com/api/v1.0/client/',
            headers=headers,
            timeout=30
        )
        
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"Content-Length: {response.headers.get('content-length', 'unknown')}")
        
        # Check if request was successful
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print("Response content:")
            print(response.text[:500])  # First 500 chars
            raise requests.RequestException(f"HTTP {response.status_code}: {response.text}")
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        if 'application/zip' not in content_type and 'application/octet-stream' not in content_type:
            print(f"Warning: Unexpected content-type: {content_type}")
            
        # Check content length
        content_length = len(response.content)
        print(f"Downloaded {content_length} bytes")
        
        if content_length < 1000:
            print("Warning: Downloaded content seems too small")
            print("Content preview:")
            print(response.text[:200])
            
        # Save to temporary file first
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            temp_file.write(response.content)
            temp_zip_path = temp_file.name
        
        # Test ZIP file validity
        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                # Test the ZIP file
                bad_file = zip_ref.testzip()
                if bad_file:
                    raise zipfile.BadZipFile(f"Corrupted file in ZIP: {bad_file}")
                
                print("✅ ZIP file is valid")
                print("ZIP contents:")
                for info in zip_ref.infolist():
                    print(f"  - {info.filename} ({info.file_size} bytes)")
                
                # Extract to target directory
                extract_dir = Path('magicpod-api-client')
                extract_dir.mkdir(exist_ok=True)
                
                zip_ref.extractall(extract_dir)
                print(f"✅ Successfully extracted to {extract_dir}")
                
                # List extracted contents
                print("Extracted files:")
                for item in extract_dir.rglob('*'):
                    if item.is_file():
                        print(f"  - {item}")
                        
        except zipfile.BadZipFile as e:
            print(f"❌ Invalid ZIP file: {e}")
            print("File header (hex):")
            with open(temp_zip_path, 'rb') as f:
                header = f.read(32)
                print(' '.join(f'{b:02x}' for b in header))
            raise
            
        finally:
            # Clean up temporary file
            os.unlink(temp_zip_path)
            
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise

if __name__ == "__main__":
    download_magicpod_client()