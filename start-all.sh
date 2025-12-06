#!/bin/bash

echo "🚀 Starting all services..."

# Start Traefik
echo "▶️  Starting Traefik..."
cd traefik && docker compose up -d && cd ..

# Start PostgreSQL
echo "▶️  Starting PostgreSQL..."
cd postgresql && docker compose up -d && cd ..

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

# Start Headwind MDM
echo "▶️  Starting Headwind MDM..."
cd headwind-mdm && docker compose up -d && cd ..

echo "✅ All services started successfully!"
docker ps
