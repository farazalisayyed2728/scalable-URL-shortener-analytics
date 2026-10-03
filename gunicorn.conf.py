import multiprocessing
import os

# Binding
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# Worker Sizing: (2 * CPU cores) + 1
workers = int(os.getenv("GUNICORN_WORKERS", (multiprocessing.cpu_count() * 2) + 1))
worker_class = "sync"

# Timeouts
timeout = 30
keepalive = 5

# Memory Leak Prevention (Worker Recycling)
# Automatically restart workers after processing 1,000 requests (with ±100 request jitter)
max_requests = 1000
max_requests_jitter = 100

# Logging: Stream directly to stdout/stderr for Docker / Kubernetes capture
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process Naming
proc_name = "shortlink_gunicorn"