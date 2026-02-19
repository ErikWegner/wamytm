# Gunicorn configuration file
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 1
worker_class = "sync"  # Changed from gevent to sync for better Oracle compatibility
worker_connections = 1000
timeout = 120  # Reduced from 300 to 120 seconds
keepalive = 5
max_requests = 500  # Reduced from 1000 to prevent memory leaks
max_requests_jitter = 50
# Disable preload_app to prevent database connection sharing across workers
preload_app = False

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "wamytm"

# Graceful timeout for worker shutdown
graceful_timeout = 30

# Enable stdio inheritance
capture_output = True
