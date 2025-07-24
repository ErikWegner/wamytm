# Gunicorn configuration file
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
#workers = multiprocessing.cpu_count() * 2 + 1
workers = 2
worker_class = "gevent"
worker_connections = 1000
timeout = 300
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
# Disable preload_app to prevent database connection sharing across workers
preload_app = False

# Restart workers after this many requests, with up to 'jitter' random
# variation, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

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
