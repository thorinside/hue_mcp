# Hue MCP Server - Docker Deployment

This guide explains how to deploy the Hue MCP Server using Docker for easy deployment on any server.

## Quick Start

### 1. Generate Hue Bridge Credentials

First, run the setup script to discover your bridge and generate credentials:

```bash
python setup.py --discover-only  # Test bridge discovery
python setup.py                  # Full setup with authentication
```

This will create a `.env` file with your bridge IP and username.

### 2. Test Network Connectivity

Ensure the Docker host can reach your Hue bridge:

```bash
# Test from host
curl http://192.168.1.64/api

# Test from container (if already built)
docker run --rm --network host hue-mcp-server:latest \
  python -c "import httpx; print('Bridge reachable:', httpx.get('http://192.168.1.64/api').status_code)"
```

### 3. Build and Run with Docker Compose

```bash
# Copy environment template
cp .env.docker .env

# Edit .env with your bridge IP and username
nano .env

# Build and run
docker-compose up -d
```

### 4. Manual Docker Commands

```bash
# Build the image
docker build -t hue-mcp-server .

# Run the container
docker run -d \
  --name hue-mcp-server \
  --restart unless-stopped \
  --network host \
  -e HUE_BRIDGE_IP=192.168.1.64 \
  -e HUE_USERNAME=your_username_here \
  hue-mcp-server
```

## Network Requirements

**Critical**: The Docker container must be able to reach your Hue bridge on the local network.

### Network Modes

#### Host Network (Recommended)
```bash
# Uses host's network stack directly
docker run --network host hue-mcp-server
```

**Pros**: Simple, direct access to local network
**Cons**: Less isolation, may conflict with host ports

#### Bridge Network
```bash
# Custom bridge network for better control
docker network create --driver bridge hue-network
docker run --network hue-network -p 8080:8080 hue-mcp-server
```

**Pros**: Better isolation, port control
**Cons**: May need additional routing for bridge discovery

#### Macvlan Network (Advanced)
```bash
# Gives container its own MAC address on the network
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 hue-macvlan

docker run --network hue-macvlan --ip=192.168.1.200 hue-mcp-server
```

**Pros**: Container appears as separate device on network
**Cons**: More complex setup, requires network configuration

### Firewall Considerations

Ensure these ports are accessible:
- **Outbound HTTP (80)**: For bridge communication
- **Outbound HTTPS (443)**: For bridge discovery via N-UPnP
- **Local Network**: Access to bridge IP (typically 192.168.1.x)

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `HUE_BRIDGE_IP` | IP address of your Hue bridge | `192.168.1.64` | ✅ |
| `HUE_USERNAME` | Bridge username (min 10 chars) | - | ✅ |
| `LOG_LEVEL` | Logging level | `INFO` | ❌ |
| `HUE_TIMEOUT_CONNECT` | Connection timeout (seconds) | `5.0` | ❌ |
| `HUE_TIMEOUT_READ` | Read timeout (seconds) | `10.0` | ❌ |
| `HUE_MAX_CONNECTIONS` | Max HTTP connections | `10` | ❌ |
| `HUE_MAX_KEEPALIVE` | Max keepalive connections | `5` | ❌ |
| `HUE_LIGHT_RATE_LIMIT` | Light ops per second | `10` | ❌ |
| `HUE_GROUP_RATE_LIMIT` | Group ops per second | `1.0` | ❌ |

## Image Details

- **Base Image**: `python:3.11-alpine` (multi-stage build)
- **Final Size**: ~143MB
- **Architecture**: Multi-arch (supports ARM64 and AMD64)
- **Security**: Runs as non-root user (`hue`)
- **Process Manager**: Uses `tini` for proper signal handling

## Features

### Multi-Stage Build
The Dockerfile uses a multi-stage build to minimize the final image size:
- **Builder stage**: Compiles dependencies and builds the wheel
- **Runtime stage**: Only installs the wheel and runtime dependencies

### Security Features
- Runs as non-root user (`hue:1000`)
- Minimal attack surface (Alpine Linux)
- No unnecessary packages in final image

### Health Checks
Built-in health check that verifies the Python environment is working.

## Deployment Examples

### Docker Compose (Recommended)

```yaml
version: '3.8'
services:
  hue-mcp:
    build: .
    restart: unless-stopped
    network_mode: "host"
    environment:
      - HUE_BRIDGE_IP=${HUE_BRIDGE_IP}
      - HUE_USERNAME=${HUE_USERNAME}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.5'
```

### Docker Swarm

```bash
# Deploy as a service
docker service create \
  --name hue-mcp-server \
  --replicas 1 \
  --network host \
  --env HUE_BRIDGE_IP=192.168.1.64 \
  --env HUE_USERNAME=your_username_here \
  --limit-memory 128M \
  --limit-cpu 0.5 \
  hue-mcp-server
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hue-mcp-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: hue-mcp-server
  template:
    metadata:
      labels:
        app: hue-mcp-server
    spec:
      containers:
      - name: hue-mcp-server
        image: hue-mcp-server:latest
        env:
        - name: HUE_BRIDGE_IP
          value: "192.168.1.64"
        - name: HUE_USERNAME
          valueFrom:
            secretKeyRef:
              name: hue-credentials
              key: username
        resources:
          limits:
            memory: "128Mi"
            cpu: "500m"
          requests:
            memory: "64Mi"
            cpu: "100m"
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker logs hue-mcp-server

# Run interactively for debugging
docker run -it --rm hue-mcp-server /bin/sh
```

### Network connectivity issues

#### Bridge not reachable
```bash
# Test from host
ping 192.168.1.64
curl http://192.168.1.64/api

# Test from container with host network
docker run --rm --network host hue-mcp-server \
  python -c "import httpx; print(httpx.get('http://192.168.1.64/api').status_code)"

# Test from container with bridge network
docker run --rm --network bridge hue-mcp-server \
  python -c "import httpx; print(httpx.get('http://192.168.1.64/api').status_code)"
```

#### Docker network issues
```bash
# Check network configuration
docker network ls
docker network inspect bridge

# Test container's network stack
docker run --rm --network host hue-mcp-server ip route
docker run --rm --network host hue-mcp-server nslookup google.com
```

#### Bridge discovery fails
```bash
# Test N-UPnP discovery
curl https://discovery.meethue.com/

# Run setup script in container
docker run --rm -it --network host hue-mcp-server python setup.py --discover-only
```

### Permission issues
```bash
# Check if running as correct user
docker exec hue-mcp-server id
# Should output: uid=1000(hue) gid=1000(hue)
```

### Common Network Solutions

#### Different subnet
If your bridge is on a different subnet (e.g., 10.0.1.x instead of 192.168.1.x):
```bash
# Update environment variable
-e HUE_BRIDGE_IP=10.0.1.64
```

#### VPN or complex network
```bash
# Use macvlan for direct network access
docker network create -d macvlan --subnet=192.168.1.0/24 --gateway=192.168.1.1 -o parent=eth0 hue-net
docker run --network hue-net --ip=192.168.1.200 hue-mcp-server
```

#### Corporate firewall
```bash
# Check if HTTP traffic is blocked
telnet 192.168.1.64 80

# Use bridge mode if host networking is restricted
docker run --network bridge -p 8080:8080 hue-mcp-server
```

## Performance

The containerized version has been optimized for minimal resource usage:
- **Memory**: ~64-128MB typical usage
- **CPU**: <0.1 CPU under normal load
- **Startup time**: <5 seconds
- **Image size**: 143MB (compressed: ~50MB)

## Security Considerations

1. **Network**: Use `--network host` for bridge discovery
2. **Secrets**: Store HUE_USERNAME in Docker secrets or env files
3. **Updates**: Rebuild periodically for security updates
4. **Logs**: Monitor logs for authentication failures