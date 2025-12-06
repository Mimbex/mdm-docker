#!/bin/bash

echo "🚀 Quick Setup for Headwind MDM with Traefik"
echo "=============================================="
echo ""

# Note: Running as root is not recommended but allowed
# if [ "$EUID" -eq 0 ]; then 
#     echo "⚠️  Please do not run this script as root"
#     exit 1
# fi

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

# Check for existing Traefik
echo "🔍 Checking for existing services..."
TRAEFIK_RUNNING=$(docker ps --filter "name=traefik" --filter "status=running" -q)
POSTGRES_RUNNING=$(docker ps --filter "name=postgres" --filter "status=running" -q)

if [ ! -z "$TRAEFIK_RUNNING" ]; then
    echo "   ℹ️  Traefik is already running (container: $(docker ps --filter "name=traefik" --format "{{.Names}}" | head -1))"
    echo "   ⚠️  Will skip Traefik setup - using existing instance"
    USE_EXISTING_TRAEFIK=true
else
    echo "   ✅ No Traefik found - will use included Traefik"
    USE_EXISTING_TRAEFIK=false
fi

if [ ! -z "$POSTGRES_RUNNING" ]; then
    echo "   ℹ️  PostgreSQL is already running (container: $(docker ps --filter "name=postgres" --format "{{.Names}}" | head -1))"
    echo "   ⚠️  Will skip PostgreSQL setup - using existing instance"
    USE_EXISTING_POSTGRES=true
else
    echo "   ✅ No PostgreSQL found - will use included PostgreSQL"
    USE_EXISTING_POSTGRES=false
fi
echo ""

# Create networks
echo "📡 Creating Docker networks..."
docker network create traefik-network 2>/dev/null && echo "   ✅ traefik-network created" || echo "   ℹ️  traefik-network already exists"
docker network create postgres-network 2>/dev/null && echo "   ✅ postgres-network created" || echo "   ℹ️  postgres-network already exists"
echo ""

# Create Let's Encrypt directory and file only if not using existing Traefik
if [ "$USE_EXISTING_TRAEFIK" = false ]; then
    echo "🔐 Setting up Let's Encrypt..."
    mkdir -p traefik/letsencrypt
    touch traefik/letsencrypt/acme.json
    chmod 600 traefik/letsencrypt/acme.json
    echo "   ✅ Let's Encrypt directory created"
    echo ""
fi

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

if [ "$USE_EXISTING_TRAEFIK" = true ] && [ "$USE_EXISTING_POSTGRES" = true ]; then
    echo ""
    echo "   ⚡ DETECTED: Existing Traefik and PostgreSQL"
    echo "   You only need to configure and start Headwind MDM"
    echo ""
    echo "   1. Edit headwind-mdm/.env:"
    echo "      - Set DOMAIN to your MDM domain"
    echo "      - Set SQL_HOST to your PostgreSQL host"
    echo "      - Set SQL_USER, SQL_PASS, SQL_BASE for your database"
    echo "      - Set FORCE_RECONFIGURE=true for first start"
    echo ""
    echo "   2. Start only Headwind MDM:"
    echo "      cd headwind-mdm && docker compose up -d"
    echo ""
    echo "   3. Check logs:"
    echo "      docker compose logs -f"
    echo ""
    echo "   4. After successful start, set FORCE_RECONFIGURE=false"
    
elif [ "$USE_EXISTING_TRAEFIK" = true ]; then
    echo ""
    echo "   ⚡ DETECTED: Existing Traefik"
    echo "   You need to configure PostgreSQL and Headwind MDM"
    echo ""
    echo "   1. Edit the .env files:"
    echo "      - postgresql/.env (set database password)"
    echo "      - headwind-mdm/.env (set your domain and credentials)"
    echo ""
    echo "   2. Set FORCE_RECONFIGURE=true in headwind-mdm/.env"
    echo ""
    echo "   3. Start PostgreSQL and Headwind MDM:"
    echo "      cd postgresql && docker compose up -d"
    echo "      cd ../headwind-mdm && docker compose up -d"
    echo ""
    echo "   4. Check status:"
    echo "      docker ps"
    
elif [ "$USE_EXISTING_POSTGRES" = true ]; then
    echo ""
    echo "   ⚡ DETECTED: Existing PostgreSQL"
    echo "   You need to configure Traefik and Headwind MDM"
    echo ""
    echo "   1. Edit the .env files:"
    echo "      - traefik/.env (set your email and domain)"
    echo "      - headwind-mdm/.env (set your domain, use existing DB credentials)"
    echo ""
    echo "   2. Set FORCE_RECONFIGURE=true in headwind-mdm/.env"
    echo ""
    echo "   3. Start Traefik and Headwind MDM:"
    echo "      cd traefik && docker compose up -d"
    echo "      cd ../headwind-mdm && docker compose up -d"
    echo ""
    echo "   4. Check status:"
    echo "      docker ps"
    
else
    echo ""
    echo "   📦 FULL INSTALLATION"
    echo "   No existing services detected"
    echo ""
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
fi

echo ""
echo "=============================================="
