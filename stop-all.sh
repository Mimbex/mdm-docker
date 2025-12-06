#!/bin/bash

echo "🛑 Stopping all services..."

# Stop Headwind MDM
echo "⏹️  Stopping Headwind MDM..."
cd headwind-mdm && docker compose down && cd ..

# Stop PostgreSQL
echo "⏹️  Stopping PostgreSQL..."
cd postgresql && docker compose down && cd ..

# Stop Traefik
echo "⏹️  Stopping Traefik..."
cd traefik && docker compose down && cd ..

echo "✅ All services stopped successfully!"
