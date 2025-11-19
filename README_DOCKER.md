# Story Generator - Docker Deployment Guide

A simple, one-container deployment of the Story Generator application. Perfect for personal use on your local machine, VPS, or cloud platforms like Coolify.

## Quick Start

### Option 1: Using Docker Run (Simplest)

```bash
docker run -d \
  --name story-generator \
  -p 8000:8000 \
  -v story-data:/app/data \
  yourusername/story-generator:latest
```

That's it! Access the app at `http://localhost:8000`

### Option 2: Using Docker Compose

1. Download the docker-compose.yml:
```bash
curl -O https://raw.githubusercontent.com/yourusername/story-generator/main/docker-compose.yml
```

2. (Optional) Create a `.env` file with your API keys:
```env
OPENAI_KEY=your_key_here
GOOGLE_API=your_key_here
STABILITY_API_KEY=your_key_here
FAL_KEY=your_key_here
```

3. Run:
```bash
docker-compose up -d
```

### Option 3: Build from Source

```bash
git clone https://github.com/yourusername/story-generator.git
cd story-generator
docker-compose up -d --build
```

## Deployment Platforms

### Deploy on Coolify

1. Create a new service in Coolify
2. Select "Docker Image" as the source
3. Enter image: `yourusername/story-generator:latest`
4. Set port to `8000`
5. Add a persistent volume:
   - Mount path: `/app/data`
   - Size: 1GB (or more if needed)
6. (Optional) Set environment variables for API keys
7. Deploy!

### Deploy on Railway

1. Create new project from Docker Image
2. Image: `yourusername/story-generator:latest`
3. Add environment variables (optional)
4. Add persistent volume at `/app/data`
5. Deploy

### Deploy on VPS

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Run the container
docker run -d \
  --name story-generator \
  -p 80:8000 \
  -v story-data:/app/data \
  --restart unless-stopped \
  yourusername/story-generator:latest

# Access at http://your-vps-ip
```

## Environment Variables

All environment variables are **optional**. You can set API keys later through the web interface.

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Auto-generated |
| `DEBUG` | Debug mode | `False` |
| `OPENAI_KEY` | OpenAI API key | - |
| `GOOGLE_API` | Google API key | - |
| `STABILITY_API_KEY` | Stability AI key | - |
| `FAL_KEY` | Fal.ai API key | - |
| `DJANGO_SUPERUSER_USERNAME` | Admin username | `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | Admin password | `admin123` |
| `DJANGO_SUPERUSER_EMAIL` | Admin email | `admin@example.com` |
| `CSRF_TRUSTED_ORIGINS` | Trusted domains | `http://localhost:8000` |

## First Time Setup

1. **Access the Application**
   - Open `http://localhost:8000` (or your domain)
   - The app is ready to use immediately

2. **Configure API Keys** (Two options)
   - Option A: Go to Settings page in the web UI
   - Option B: Set environment variables before running

3. **Access Admin Panel** (Optional)
   - Go to `http://localhost:8000/admin`
   - Default credentials: `admin` / `admin123`
   - Change these immediately in production!

## Data Persistence

All your data is stored in a Docker volume:
- Database (SQLite)
- Uploaded media files
- Generated images

The volume persists even if you remove and recreate the container.

### Backup Your Data

```bash
# Create backup
docker run --rm -v story-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/story-backup.tar.gz -C /data .

# Restore backup
docker run --rm -v story-data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/story-backup.tar.gz -C /data
```

## Updating

```bash
# Pull latest image
docker pull yourusername/story-generator:latest

# Restart container
docker-compose down && docker-compose up -d

# Or with docker run
docker stop story-generator
docker rm story-generator
docker run -d \
  --name story-generator \
  -p 8000:8000 \
  -v story-data:/app/data \
  yourusername/story-generator:latest
```

## Custom Domain Setup

If deploying with a custom domain:

1. Set the CSRF_TRUSTED_ORIGINS environment variable:
```env
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

2. For HTTPS (recommended), use a reverse proxy like nginx or Caddy, or deploy on platforms that handle SSL automatically (Coolify, Railway, etc.)

## Troubleshooting

### Container won't start
```bash
docker logs story-generator
```

### Reset admin password
```bash
docker exec -it story-generator python manage.py changepassword admin --settings=settings_docker
```

### Access Django shell
```bash
docker exec -it story-generator python manage.py shell --settings=settings_docker
```

### Check disk usage
```bash
docker system df
docker volume ls
```

## Resource Requirements

- **Minimum**: 512MB RAM, 1GB disk space
- **Recommended**: 1GB RAM, 5GB disk space
- **CPU**: 1 core is sufficient for personal use
- **Storage**: Grows with uploaded/generated images

## Security Notes

1. **Change default admin credentials** immediately
2. **Use HTTPS** in production (platforms like Coolify handle this automatically)
3. **Keep SECRET_KEY** private and consistent across deployments
4. **Regular backups** are recommended

## Building for Docker Hub

If you want to build and push your own image:

```bash
# Build the image
docker build -t yourusername/story-generator:latest .

# Test locally
docker run -p 8000:8000 yourusername/story-generator:latest

# Push to Docker Hub
docker login
docker push yourusername/story-generator:latest
```

## Support

- Issues: [GitHub Issues](https://github.com/yourusername/story-generator/issues)
- Documentation: [Main README](README.md)

---

Made with ❤️ for easy, personal story generation