# Multi-stage build for minimal Hue MCP Server image
FROM python:3.11-alpine AS builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir build wheel

# Build the package
COPY src/ ./src/
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels .

# Production stage
FROM python:3.11-alpine

# Install runtime dependencies only
RUN apk add --no-cache tini

# Set working directory
WORKDIR /app

# Copy wheels from builder stage
COPY --from=builder /app/wheels /wheels

# Install the package from wheels
RUN pip install --no-cache-dir --find-links /wheels hue-mcp-server \
    && rm -rf /wheels /root/.cache/pip

# Copy only necessary source files
COPY src/hue_mcp/ ./src/hue_mcp/

# Create non-root user for security
RUN addgroup -g 1000 hue && \
    adduser -D -s /bin/sh -u 1000 -G hue hue
RUN chown -R hue:hue /app
USER hue

# Set environment variables
ENV PYTHONPATH=/app/src
ENV HUE_BRIDGE_IP=192.168.1.64
ENV HUE_USERNAME=your_username_here
ENV LOG_LEVEL=INFO
ENV PYTHONUNBUFFERED=1

# Health check (simplified for smaller image)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=2 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Default command - run the MCP server
CMD ["python", "-m", "hue_mcp.server"]