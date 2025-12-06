#!/bin/bash

echo "📊 Checking status of all services..."
echo "======================================"
echo ""

# Check Traefik
echo "🔍 Traefik Status:"
cd traefik && docker compose ps && cd ..
echo ""

# Check PostgreSQL
echo "🔍 PostgreSQL Status:"
cd postgresql && docker compose ps && cd ..
echo ""

# Check Headwind MDM
echo "🔍 Headwind MDM Status:"
cd headwind-mdm && docker compose ps && cd ..
echo ""

echo "======================================"
echo "📊 All Services Overview:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
