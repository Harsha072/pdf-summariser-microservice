#!/bin/bash
# ========================================
# SSL Certificate Setup with Let's Encrypt
# ========================================
set -e

# Check if domain is provided
if [ -z "$1" ]; then
    echo "❌ Error: Domain name required"
    echo "Usage: sudo ./setup-ssl.sh yourdomain.com"
    exit 1
fi

DOMAIN=$1
EMAIL=${2:-admin@$DOMAIN}

echo "🔒 Setting up SSL for: $DOMAIN"
echo "📧 Admin email: $EMAIL"

# Stop nginx temporarily
cd /home/ubuntu/pdf-summariser
docker-compose -f docker-compose.prod.yml stop nginx

# Obtain certificate
certbot certonly --standalone \
    -d $DOMAIN \
    -d www.$DOMAIN \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    --preferred-challenges http

# Start nginx
docker-compose -f docker-compose.prod.yml start nginx

# Setup auto-renewal
(crontab -l 2>/dev/null; echo "0 0 * * 0 certbot renew --quiet --deploy-hook 'cd /home/ubuntu/pdf-summariser && docker-compose -f docker-compose.prod.yml restart nginx'") | crontab -

echo "✅ SSL certificate installed successfully!"
echo "🔄 Auto-renewal configured (runs weekly)"
echo ""
echo "Your application is now available at:"
echo "   https://$DOMAIN"
