#!/bin/bash

# Check if API token is set
if [ -z "$MAGICPOD_API_TOKEN" ]; then
    echo "Error: MAGICPOD_API_TOKEN environment variable is not set"
    exit 1
fi

echo "Downloading MagicPod API client..."

# Download with verbose output and error handling
response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
    -H "Authorization: Token ${MAGICPOD_API_TOKEN}" \
    -H "Accept: application/zip" \
    -o magicpod-api-client.zip \
    https://app.magicpod.com/api/v1.0/client/)

# Extract the HTTP status code
http_code=$(echo $response | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')

echo "HTTP Status Code: $http_code"

# Check if download was successful
if [ "$http_code" -ne 200 ]; then
    echo "Error: Failed to download MagicPod API client. HTTP status: $http_code"
    echo "Response content:"
    cat magicpod-api-client.zip
    exit 1
fi

# Check if downloaded file is actually a ZIP file
file_type=$(file magicpod-api-client.zip)
echo "Downloaded file type: $file_type"

if [[ $file_type != *"Zip archive"* ]]; then
    echo "Error: Downloaded file is not a valid ZIP archive"
    echo "File content preview:"
    head -n 10 magicpod-api-client.zip
    exit 1
fi

# Check file size
file_size=$(stat -c%s magicpod-api-client.zip 2>/dev/null || stat -f%z magicpod-api-client.zip 2>/dev/null)
echo "Downloaded file size: $file_size bytes"

if [ "$file_size" -lt 1000 ]; then
    echo "Warning: Downloaded file seems too small. Content:"
    cat magicpod-api-client.zip
    exit 1
fi

# Test ZIP integrity before extracting
echo "Testing ZIP file integrity..."
if ! unzip -t magicpod-api-client.zip > /dev/null 2>&1; then
    echo "Error: ZIP file is corrupted or invalid"
    echo "File content:"
    hexdump -C magicpod-api-client.zip | head -n 5
    exit 1
fi

# Extract the ZIP file
echo "Extracting MagicPod API client..."
if unzip -q magicpod-api-client.zip -d magicpod-api-client; then
    echo "✅ Successfully downloaded and extracted MagicPod API client"
    ls -la magicpod-api-client/
else
    echo "❌ Failed to extract ZIP file"
    exit 1
fi