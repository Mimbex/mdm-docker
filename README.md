# Docker Traefik + Headwind MDM + PostgreSQL

Complete production-ready stack with Traefik as reverse proxy, automatic SSL certificates with Let's Encrypt, PostgreSQL 17, and Headwind MDM.

## 📋 Project Structure

```
mdm-docker/
├── traefik/              # Reverse proxy with automatic SSL
│   ├── docker-compose.yml
│   ├── .env
│   └── .env.example
├── postgresql/           # PostgreSQL 17 database
│   ├── docker-compose.yml
│   ├── .env
│   └── .env.example
├── headwind-mdm/         # Headwind MDM server
│   ├── docker-compose.yml
│   ├── .env
│   └── .env.example
├── build-all.sh          # Script to build all services
├── start-all.sh          # Script to start all services
├── stop-all.sh           # Script to stop all services
├── status-all.sh         # Script to check status of all services
├── quick-setup.sh        # Quick setup script (automated)
├── .gitignore
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Root or sudo access for network creation
- Domain names pointing to your server

### Option A: Automated Setup (Recommended)

Run the quick setup script to automatically configure networks and environment files:

```bash
./quick-setup.sh
```

Then follow the instructions to edit the `.env` files and start the services.

### Option B: Manual Setup

### 1. Configure Docker Networks

```bash
docker network create traefik-network
docker network create postgres-network
```

### 2. Configure Let's Encrypt Permissions

```bash
mkdir -p traefik/letsencrypt
touch traefik/letsencrypt/acme.json
chmod 600 traefik/letsencrypt/acme.json
```

### 3. Configure Domains

Copy the `.env.example` files to `.env` in each folder and edit them:

```bash
cp traefik/.env.example traefik/.env
cp postgresql/.env.example postgresql/.env
cp headwind-mdm/.env.example headwind-mdm/.env
```

Then edit the `.env` files in each folder:

#### traefik/.env

```env
LETS_ENCRYPT_CONTACT_EMAIL=your-email@example.com
DOMAIN_NAME=traefik.yourdomain.com
```

#### postgresql/.env

```env
POSTGRES_DB=hmdm
POSTGRES_PASSWORD=hmdm
POSTGRES_USER=hmdm
```

#### headwind-mdm/.env

```env
SQL_BASE=hmdm
SQL_USER=hmdm
SQL_PASS=hmdm

ADMIN_EMAIL=admin@yourdomain.com
DOMAIN=mdm.yourdomain.com

# This parameter should be set to the local IP address
# if your server is behind the NAT
LOCAL_IP=

# Turn on this parameter once you change variables!
# After a successful start, turn this parameter back off
FORCE_RECONFIGURE=false

# Update the shared secret in Premium setup!
SHARED_SECRET=changeme-C3z9vi54

HMDM_VARIANT=os
DOWNLOAD_CREDENTIALS=
HMDM_URL=https://h-mdm.com/files/hmdm-5.33.2-os.war
CLIENT_VERSION=6.18
```

**Important:** Set `FORCE_RECONFIGURE=true` for the first start, then change it back to `false` after successful initialization.

### 4. Build and Start Services

```bash
# Build all services
./build-all.sh

# Start all services
./start-all.sh

# Check status
docker ps
```

## 🌐 Service Access

After starting all services, you can access:

- **Headwind MDM**: `https://mdm.yourdomain.com`
- **Traefik Dashboard**: `https://traefik.yourdomain.com`

Default Headwind MDM credentials:
- Username: `admin`
- Password: `admin` (change it after first login)

## ⚙️ Domain Configuration

### Change Headwind MDM Domain

Edit `headwind-mdm/.env`:

```env
DOMAIN=your-new-domain.com
```

Then restart the service:

```bash
cd headwind-mdm && docker compose down && docker compose up -d && cd ..
```

### Change Traefik Domain

Edit `traefik/.env`:

```env
DOMAIN_NAME=traefik.your-new-domain.com
```

Then restart the service:

```bash
cd traefik && docker compose down && docker compose up -d && cd ..
```

### Using Premium Version

To run Premium version, you need to change the following variables in `headwind-mdm/.env`:

- `HMDM_VARIANT`
- `DOWNLOAD_CREDENTIALS`
- `HMDM_URL`

To get the trial URLs, credentials and license keys, please fill the form at: https://h-mdm.com/contact-us/

## 🛠️ Management Scripts

### build-all.sh

Builds all Docker images for the services.

```bash
./build-all.sh
```

### start-all.sh

Starts all services in the correct order (Traefik → PostgreSQL → Headwind MDM).

```bash
./start-all.sh
```

### stop-all.sh

Stops all services in reverse order.

```bash
./stop-all.sh
```

### status-all.sh

Checks the status of all services.

```bash
./status-all.sh
```

## 📦 Included Services

### Traefik (Reverse Proxy)

- Automatic SSL certificate generation with Let's Encrypt
- HTTP to HTTPS redirection
- Dashboard available at configured domain
- Ports: 80 (HTTP), 443 (HTTPS), 8080 (Dashboard)

### PostgreSQL

- Version: 17
- Database: hmdm
- Persistent data storage
- Connected via internal network

### Headwind MDM

- Official Docker image: `headwindmdm/hmdm:0.1.5`
- Automatic SSL configuration
- Integrated with Traefik for reverse proxy
- Persistent configuration and work data
- Port 31000 for device communication

## 🔧 Useful Commands

### View service logs

```bash
# Headwind MDM logs
cd headwind-mdm && docker compose logs -f

# PostgreSQL logs
cd postgresql && docker compose logs -f

# Traefik logs
cd traefik && docker compose logs -f
```

### Restart a specific service

```bash
cd <service-folder> && docker compose restart && cd ..
```

### Rebuild a service

```bash
cd <service-folder> && docker compose down && docker compose build && docker compose up -d && cd ..
```

### Check network status

```bash
docker network ls
docker network inspect traefik-network
docker network inspect postgres-network
```

### Access Headwind MDM container

```bash
docker exec -it <container-id> /bin/bash
```

## 🔒 Security

- All services use HTTPS with automatic SSL certificates
- PostgreSQL is not exposed to the internet (internal network only)
- Change default passwords in `.env` files before production use
- Update `SHARED_SECRET` in `headwind-mdm/.env` for production
- Keep Docker and images updated regularly

## 📝 Important Notes

1. **First Start**: Set `FORCE_RECONFIGURE=true` in `headwind-mdm/.env` for the first start, then change it back to `false`
2. **DNS Configuration**: Make sure your domains point to your server's IP address
3. **Firewall**: Open ports 80, 443, and 31000 in your firewall
4. **Let's Encrypt Rate Limits**: Be careful with certificate generation to avoid hitting rate limits
5. **Backup**: Regularly backup PostgreSQL data and Headwind MDM volumes
6. **Production**: Change all default passwords and secrets before deploying to production

## 🐛 Troubleshooting

### Error: "network not found"

Make sure you created the required networks:

```bash
docker network create traefik-network
docker network create postgres-network
```

### Error: "acme.json permission denied"

Fix the permissions:

```bash
chmod 600 traefik/letsencrypt/acme.json
```

### Headwind MDM doesn't connect to PostgreSQL

1. Check if PostgreSQL is running: `docker ps`
2. Verify database credentials in both `postgresql/.env` and `headwind-mdm/.env`
3. Check PostgreSQL logs: `cd postgresql && docker compose logs -f`

### SSL certificate not generated

1. Verify your domain points to your server
2. Check if ports 80 and 443 are open
3. Review Traefik logs: `cd traefik && docker compose logs -f`
4. Ensure `acme.json` has correct permissions (600)

### Headwind MDM initialization fails

1. Set `FORCE_RECONFIGURE=true` in `headwind-mdm/.env`
2. Restart the service: `cd headwind-mdm && docker compose down && docker compose up -d`
3. Check logs: `docker compose logs -f`
4. After successful start, set `FORCE_RECONFIGURE=false`

### Reset Headwind MDM

To completely reset Headwind MDM:

```bash
cd headwind-mdm
docker compose down -v
cd ..
```

This will remove all volumes and data. Then start again with `FORCE_RECONFIGURE=true`.

## 📚 Additional Resources

- [Headwind MDM Official Documentation](https://h-mdm.com/documentation/)
- [Headwind MDM Docker Repository](https://github.com/h-mdm/hmdm-docker)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 📄 About

Part of the Mimbex Docker infrastructure series.

Related projects:
- [docker-traefik](https://github.com/Mimbex/docker-traefik) - Traefik + Odoo + PostgreSQL

---

**By Dustin Mimbela**
