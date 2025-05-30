#!/bin/bash
curl -H "Authorization: Token ${MAGICPOD_API_TOKEN}" \
     -o magicpod-api-client.zip \
     https://app.magicpod.com/api/v1.0/client/
unzip magicpod-api-client.zip -d magicpod-api-client