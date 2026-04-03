# Deploy Backend To VPS (Docker Compose)

This deployment path runs:

- FastAPI backend
- PostgreSQL
- MQTT broker
- Optional sensor/device simulators for demo mode

## 1. Prepare VPS

Install Docker Engine + Docker Compose plugin.

Open inbound ports:

- `80` and `443` for HTTPS reverse proxy
- `1883` only if external MQTT clients need direct access

## 2. Upload project and prepare env

From `web-backend` directory on VPS:

```bash
cp .env.prod.example .env.prod
```

Then edit `.env.prod`:

- set `POSTGRES_PASSWORD`
- set `SECRET_KEY`
- set `BACKEND_DOMAIN` to your real API domain (for example `api.yourdomain.com`)
- set `ACME_EMAIL` for Let's Encrypt
- set SMTP values if needed
- confirm `BACKEND_IMAGE` points to your GHCR image

Create local folders used by Nginx and certbot:

```bash
mkdir -p docker/letsencrypt docker/certbot-webroot
```

## 3. Login to GHCR on VPS

Use a GitHub token that has `read:packages`.

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GITHUB_USERNAME" --password-stdin
```

## 4. Start backend stack (without edge)

Backend + DB + MQTT only:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

Run with simulator services (demo mode):

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile demo up -d
```

## 5. Issue TLS certificate (Let's Encrypt)

Run this once after DNS for `BACKEND_DOMAIN` points to your VPS public IP:

```bash
source .env.prod
docker run --rm -it \
	-p 80:80 \
	-v "$(pwd)/docker/letsencrypt:/etc/letsencrypt" \
	-v "$(pwd)/docker/certbot-webroot:/var/www/certbot" \
	certbot/certbot certonly --standalone \
	-d "$BACKEND_DOMAIN" \
	--email "$ACME_EMAIL" \
	--agree-tos --no-eff-email
```

## 6. Start edge proxy (Nginx HTTPS)

```bash
docker compose --env-file .env.prod \
	-f docker-compose.prod.yml \
	-f docker-compose.edge.yml up -d
```

To include simulators in demo mode:

```bash
docker compose --env-file .env.prod \
	-f docker-compose.prod.yml \
	-f docker-compose.edge.yml \
	--profile demo up -d
```

## 7. Verify

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
curl https://$BACKEND_DOMAIN/health
```

## 8. Update after new CD image

Pull latest image and restart services:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml pull
docker compose --env-file .env.prod -f docker-compose.prod.yml --profile demo up -d
```

If you do not use simulators in production, remove `--profile demo`.

If you also run edge proxy, include both files:

```bash
docker compose --env-file .env.prod \
	-f docker-compose.prod.yml \
	-f docker-compose.edge.yml pull
docker compose --env-file .env.prod \
	-f docker-compose.prod.yml \
	-f docker-compose.edge.yml --profile demo up -d
```

## 9. Frontend env to point at this backend

In Vercel for frontend project:

- `VITE_API_URL=https://your-backend-domain`
- `VITE_SOCKET_URL=wss://your-backend-domain/ws/alerts`
