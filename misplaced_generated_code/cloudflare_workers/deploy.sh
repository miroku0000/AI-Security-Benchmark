#!/bin/bash

echo "Deploying Cloudflare Workers Microservices Architecture"

echo "1. Deploying cache-service..."
wrangler deploy --config wrangler.toml --name cache-service

echo "2. Deploying data-service..."
wrangler deploy --config wrangler.toml --name data-service

echo "3. Deploying analytics-service..."
wrangler deploy --config wrangler.toml --name analytics-service

echo "4. Deploying auth-service..."
wrangler deploy --config wrangler.toml --name auth-service

echo "5. Deploying user-service..."
wrangler deploy --config wrangler.toml --name user-service

echo "6. Deploying gateway-worker..."
wrangler deploy --config wrangler.toml --name gateway-worker

echo "Deployment complete!"
echo "Gateway endpoint: https://gateway-worker.<your-subdomain>.workers.dev"