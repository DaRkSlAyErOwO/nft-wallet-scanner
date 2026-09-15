#!/bin/bash
# Fetch a 7-day instant API key from OpenSea

echo "Fetching OpenSea API Key..."
# Note: This curls the endpoint as required.
RESPONSE=$(curl -s -X POST https://api.opensea.io/api/v2/auth/keys)
echo "Response: $RESPONSE"
echo ""
echo "Extract your key from the response and add it to your .env file:"
echo "echo \"OPENSEA_API_KEY=<your-key>\" >> .env"
