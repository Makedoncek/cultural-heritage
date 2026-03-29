#!/bin/bash
# CultureMap Ukraine — Oracle Cloud Deployment Script
# Run on a fresh Ubuntu VM with Docker installed.
#
# Usage:
#   1. SSH into your Oracle Cloud VM
#   2. Clone the repo: git clone <your-repo-url> culturemap && cd culturemap
#   3. Copy and edit env: cp .env.example backend/.env && nano backend/.env
#   4. Run: bash deploy.sh your-domain.com your-email@gmail.com

set -e

DOMAIN=${1:?"Usage: bash deploy.sh <domain> <email>"}
EMAIL=${2:?"Usage: bash deploy.sh <domain> <email>"}

echo "=== CultureMap Deployment ==="
echo "Domain: $DOMAIN"
echo "Email:  $EMAIL"
echo ""

# Step 1: Replace ${DOMAIN} placeholder in nginx config
echo "[1/5] Configuring nginx for $DOMAIN..."
sed -i "s/\${DOMAIN}/$DOMAIN/g" nginx/nginx.conf

# Step 2: Get initial SSL certificate (before starting nginx with SSL)
# First, start a temporary nginx to serve ACME challenge
echo "[2/5] Obtaining SSL certificate..."
docker compose -f docker-compose.prod.yml up -d frontend
sleep 5

docker compose -f docker-compose.prod.yml run --rm certbot \
    certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# Step 3: Stop temporary nginx
docker compose -f docker-compose.prod.yml down

# Step 4: Start all services
echo "[3/5] Starting all services..."
docker compose -f docker-compose.prod.yml up -d --build

# Step 5: Create superuser reminder
echo ""
echo "[4/5] Creating Django superuser..."
echo "Run this command to create an admin user:"
echo "  docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser"
echo ""

echo "[5/5] Done!"
echo ""
echo "=== Deployment Complete ==="
echo "Frontend: https://$DOMAIN"
echo "Admin:    https://$DOMAIN/admin/"
echo "API:      https://$DOMAIN/api/"
echo "API Docs: https://$DOMAIN/api/docs/ (only if DEBUG=True)"
echo ""
echo "To seed test data:"
echo "  docker compose -f docker-compose.prod.yml exec backend python manage.py seed_data"
