#!/bin/bash

echo "🚀 Quick Setup for Headwind MDM with Traefik"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Please do not run this script as root"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "   Please install Docker and Docker Compose first"
    exit 1
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    echo "   Please install Docker and Docker Compose first"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Create networks
echo "📡 Creating Docker networks..."
docker network create traefik-network 2>/dev/null && echo "   ✅ traefik-network created" || echo "   ℹ️  traefik-network already exists"
docker network create postgres-network 2>/dev/null && echo "   ✅ postgres-network created" || echo "   ℹ️  postgres-network already exists"
echo ""

# Create Let's Encrypt directory and file
echo "🔐 Setting up Let's Encrypt..."
mkdir -p traefik/letsencrypt
touch traefik/letsencrypt/acme.json
chmod 600 traefik/letsencrypt/acme.json
echo "   ✅ Let's Encrypt directory created"
echo ""

# Copy .env.example files if .env doesn't exist
echo "⚙️  Setting up environment files..."
for dir in traefik postgresql headwind-mdm; do
    if [ ! -f "$dir/.env" ]; then
        cp "$dir/.env.example" "$dir/.env"
        echo "   ✅ $dir/.env created from example"
    else
        echo "   ℹ️  $dir/.env already exists"
    fi
done
echo ""

echo "=============================================="
echo "✅ Quick setup completed!"
echo ""
echo "📝 Next steps:"
echo "   1. Edit the .env files in each folder:"
echo "      - traefik/.env (set your email and domain)"
echo "      - postgresql/.env (set database password)"
echo "      - headwind-mdm/.env (set your domain and credentials)"
echo ""
echo "   2. Important: Set FORCE_RECONFIGURE=true in headwind-mdm/.env"
echo "      for the first start, then change it back to false"
echo ""
echo "   3. Build and start services:"
echo "      ./build-all.sh"
echo "      ./start-all.sh"
echo ""
echo "   4. Check status:"
echo "      ./status-all.sh"
echo ""
echo "=============================================="
