# Docker Image Security Best Practices

This project provides multiple Dockerfile options for different security and deployment requirements.

## Available Dockerfiles

### 1. `docker/Dockerfile` (Default - Recommended)

**Multi-stage build with Python slim**

- ✅ Separates build and runtime environments
- ✅ Removes build tools from final image
- ✅ Non-root user
- ✅ Minimal base image (python:3.12-slim)
- **Size**: ~150-200MB
- **Best for**: General production use, good balance of security and compatibility

### 2. `docker/Dockerfile.optimized`

**Pre-compiled wheels optimization**

- ✅ All dependencies pre-compiled as wheels
- ✅ Removes Python cache files
- ✅ Minimal runtime dependencies
- ✅ Non-root user with nologin shell
- **Size**: ~120-150MB
- **Best for**: Maximum size reduction while maintaining compatibility

### 3. `docker/Dockerfile.ubi`

**Red Hat Universal Base Image**

- ✅ Enterprise-grade security (RHEL-based)
- ✅ Regularly updated with security patches
- ✅ Freely redistributable
- ✅ Non-root user (UBI default)
- **Size**: ~200-250MB
- **Best for**: Enterprise environments, compliance requirements

### 4. `docker/Dockerfile.distroless`

**Google Distroless (Maximum Security)**

- ✅ No shell, package managers, or unnecessary tools
- ✅ Minimal attack surface
- ✅ Only application and runtime dependencies
- ⚠️ Note: Currently uses Python 3.11 (distroless doesn't have 3.12 yet)
- **Size**: ~80-100MB
- **Best for**: Maximum security, minimal attack surface

## Security Features

All Dockerfiles implement:

1. **Multi-stage builds**: Build tools never enter the final image
2. **Non-root user**: Applications run as unprivileged user (UID 1000 or 1001)
3. **Minimal base images**: Only essential runtime dependencies
4. **No build tools in runtime**: Compilers and build dependencies removed
5. **Health checks**: Container health monitoring
6. **Layer optimization**: Efficient layer caching

## Building Images

```bash
# Default (recommended)
docker build -f docker/Dockerfile -t mvg-departures:latest .

# Optimized
docker build -f docker/Dockerfile.optimized -t mvg-departures:optimized .

# UBI
docker build -f docker/Dockerfile.ubi -t mvg-departures:ubi .

# Distroless
docker build -f docker/Dockerfile.distroless -t mvg-departures:distroless .
```

## Security Recommendations

1. **Regular Updates**: Keep base images updated

   ```bash
   docker pull python:3.12-slim
   docker pull registry.access.redhat.com/ubi9/python-312:latest
   ```

2. **Scan Images**: Use security scanners

   ```bash
   docker scan mvg-departures:latest
   # or
   trivy image mvg-departures:latest
   ```

3. **Use Specific Tags**: Avoid `latest` in production

   ```bash
   docker build -f docker/Dockerfile -t mvg-departures:v1.0.0 .
   ```

4. **Read-only Filesystem**: Consider using read-only root filesystem

   ```yaml
   # docker-compose.yml
   security_opt:
     - no-new-privileges:true
   read_only: true
   tmpfs:
     - /tmp
   ```

5. **Resource Limits**: Set appropriate limits
   ```yaml
   deploy:
     resources:
       limits:
         cpus: "1"
         memory: 512M
   ```

## Size Comparison

| Dockerfile                   | Base Image         | Approx Size | Security Level |
| ---------------------------- | ------------------ | ----------- | -------------- |
| docker/Dockerfile            | python:3.12-slim   | ~180MB      | High           |
| docker/Dockerfile.optimized  | python:3.12-slim   | ~140MB      | High           |
| docker/Dockerfile.ubi        | ubi9/python-312    | ~220MB      | Very High      |
| docker/Dockerfile.distroless | distroless/python3 | ~90MB       | Maximum        |

## Choosing the Right Image

- **General Production**: Use `docker/Dockerfile` (default)
- **Size-Critical**: Use `docker/Dockerfile.optimized`
- **Enterprise/Compliance**: Use `docker/Dockerfile.ubi`
- **Maximum Security**: Use `docker/Dockerfile.distroless` (when Python 3.12 support is available)

## Troubleshooting

### Distroless Issues

- No shell available for debugging
- Use `docker exec` with full Python path: `/usr/local/bin/python3`
- Consider using `docker/Dockerfile` for development

### UBI Issues

- Requires Red Hat registry access (public, no auth needed)
- May need to configure registry mirrors in some environments

### Permission Issues

- Ensure application files are owned by the non-root user
- Check file permissions in the container
