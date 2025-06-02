#!/usr/bin/env python3
import os
import requests
import zipfile
import tempfile
from pathlib import Path
import shutil

def download_magicpod_client():
    """Download and extract MagicPod API client with improved error handling and fixed headers"""
    
    print("🚀 Starting MagicPod API client download...")
    
    # Check if API token is set
    api_token = os.getenv('MAGICPOD_API_TOKEN')
    if not api_token:
        raise ValueError("❌ MAGICPOD_API_TOKEN environment variable is not set")
    
    # Fixed headers - remove problematic Accept header
    headers = {
        'Authorization': f'Token {api_token}',
        'User-Agent': 'MagicPod-GitHub-Action/1.0'
        # Removed 'Accept': 'application/zip' as it causes 406 error
    }
    
    # Try different possible endpoints
    possible_urls = [
        'https://app.magicpod.com/api/v1.0/magicpod-clients/api/mac/latest/',
        'https://app.magicpod.com/api/v1.0/client/',
        'https://app.magicpod.com/api/v1.0/magicpod-clients/latest/'
    ]
    
    download_successful = False
    
    for download_url in possible_urls:
        try:
            print(f"📡 Trying download from: {download_url}")
            
            # Download with streaming to handle large files
            response = requests.get(
                download_url,
                headers=headers,
                timeout=60,
                stream=True
            )
            
            print(f"📊 HTTP Status: {response.status_code}")
            print(f"📄 Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            # Check if request was successful
            if response.status_code == 200:
                print(f"✅ Successfully connected to: {download_url}")
                download_successful = True
                break
            elif response.status_code == 406:
                print(f"⚠️  406 Not Acceptable from {download_url}, trying next URL...")
                continue
            else:
                print(f"❌ HTTP {response.status_code} from {download_url}")
                continue
                
        except requests.RequestException as e:
            print(f"⚠️  Connection failed to {download_url}: {e}")
            continue
    
    if not download_successful:
        # If all URLs failed, try with minimal headers
        print("🔄 Trying with minimal headers...")
        minimal_headers = {'Authorization': f'Token {api_token}'}
        
        for download_url in possible_urls:
            try:
                response = requests.get(
                    download_url,
                    headers=minimal_headers,
                    timeout=60,
                    stream=True
                )
                
                if response.status_code == 200:
                    print(f"✅ Success with minimal headers: {download_url}")
                    download_successful = True
                    break
                    
            except requests.RequestException:
                continue
    
    if not download_successful:
        error_msg = "❌ Failed to download from all attempted URLs"
        print(error_msg)
        print("🔍 Attempted URLs:")
        for url in possible_urls:
            print(f"   • {url}")
        raise requests.RequestException(error_msg)
    
    # Check content type
    content_type = response.headers.get('content-type', '').lower()
    print(f"📄 Final Content-Type: {content_type}")
    
    # Accept various content types that might contain ZIP files
    acceptable_types = ['zip', 'octet-stream', 'binary', 'application/zip']
    if not any(t in content_type for t in acceptable_types):
        print(f"⚠️  Unexpected content-type: {content_type}")
        print("⚠️  Proceeding anyway as some APIs don't set correct content-type...")
    
    # Create temporary file for download
    temp_zip_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            temp_zip_path = temp_file.name
            
            # Download with progress
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            print(f"💾 Downloading... (Total: {total_size} bytes)" if total_size else "💾 Downloading...")
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # Show progress for large files
                    if total_size > 0 and downloaded_size % (1024 * 1024) == 0:  # Every MB
                        progress = (downloaded_size / total_size) * 100
                        print(f"📈 Progress: {progress:.1f}% ({downloaded_size:,} / {total_size:,} bytes)")
        
        print(f"✅ Downloaded {downloaded_size:,} bytes")
        
        # Validate file size
        if downloaded_size < 1000:
            print(f"⚠️  Downloaded file seems too small: {downloaded_size} bytes")
            with open(temp_zip_path, 'rb') as f:
                content_preview = f.read(200)
                print(f"Content preview: {content_preview}")
                
                # Check if it's actually an error message
                try:
                    error_text = content_preview.decode('utf-8', errors='ignore')
                    if 'error' in error_text.lower() or 'not found' in error_text.lower():
                        raise Exception(f"Downloaded content appears to be an error message: {error_text}")
                except:
                    pass
        
        # Test ZIP file validity
        print("🔍 Validating ZIP file...")
        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                # Test the ZIP file integrity
                bad_file = zip_ref.testzip()
                if bad_file:
                    raise zipfile.BadZipFile(f"Corrupted file in ZIP: {bad_file}")
                
                # List contents
                file_list = zip_ref.infolist()
                print(f"✅ ZIP file is valid with {len(file_list)} files:")
                
                total_uncompressed = sum(info.file_size for info in file_list)
                print(f"📊 Total uncompressed size: {total_uncompressed:,} bytes")
                
                # Show first few files
                for i, info in enumerate(file_list[:5]):
                    print(f"   📄 {info.filename} ({info.file_size:,} bytes)")
                
                if len(file_list) > 5:
                    print(f"   ... and {len(file_list) - 5} more files")
                
                # Extract to target directory
                extract_dir = Path('magicpod-api-client')
                
                # Remove existing directory if it exists
                if extract_dir.exists():
                    print(f"🗑️  Removing existing directory: {extract_dir}")
                    shutil.rmtree(extract_dir)
                
                extract_dir.mkdir(exist_ok=True)
                
                print(f"📦 Extracting to: {extract_dir}")
                zip_ref.extractall(extract_dir)
                
                # Verify extraction
                extracted_files = list(extract_dir.rglob('*'))
                file_count = len([f for f in extracted_files if f.is_file()])
                
                print(f"✅ Successfully extracted {file_count} files")
                
                # Show some extracted files
                print("📁 Extracted structure:")
                for item in sorted(extract_dir.iterdir())[:10]:
                    if item.is_file():
                        print(f"   📄 {item.name} ({item.stat().st_size:,} bytes)")
                    elif item.is_dir():
                        subfile_count = len(list(item.rglob('*')))
                        print(f"   📁 {item.name}/ ({subfile_count} items)")
                
                # Look for main executable or important files
                important_files = []
                for pattern in ['*.jar', '*.exe', '*magicpod*', '*client*']:
                    important_files.extend(extract_dir.glob(pattern))
                
                if important_files:
                    print("🎯 Important files found:")
                    for file in important_files[:5]:
                        print(f"   ⭐ {file.name}")
                
        except zipfile.BadZipFile as e:
            print(f"❌ Invalid ZIP file: {e}")
            
            # Show file header for debugging
            with open(temp_zip_path, 'rb') as f:
                header = f.read(32)
                print(f"File header (hex): {' '.join(f'{b:02x}' for b in header)}")
                
            # Show readable content if any
            with open(temp_zip_path, 'rb') as f:
                content = f.read(500)
                try:
                    readable = content.decode('utf-8', errors='ignore')
                    if readable.strip():
                        print(f"Readable content: {readable[:200]}...")
                        
                        # Check if it's a JSON error response
                        if readable.strip().startswith('{') and 'error' in readable.lower():
                            print("⚠️  Received JSON error response instead of ZIP file")
                            
                except:
                    pass
                    
            raise
            
    finally:
        # Clean up temporary file
        if temp_zip_path and os.path.exists(temp_zip_path):
            os.unlink(temp_zip_path)

def main():
    """Main function with proper error handling"""
    try:
        download_magicpod_client()
        print("🎉 MagicPod API client download completed successfully!")
        return 0
    except Exception as e:
        print(f"💥 Download failed: {e}")
        print("\n🔍 Troubleshooting tips:")
        print("1. Verify your MAGICPOD_API_TOKEN is correct and has proper permissions")
        print("2. Check if the MagicPod API endpoint URL has changed")
        print("3. Ensure your token has access to download the API client")
        print("4. Contact MagicPod support if the issue persists")
        return 1

if __name__ == "__main__":
    exit(main())