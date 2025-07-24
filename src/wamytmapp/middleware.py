"""
Custom middleware for handling database connections and timeouts.
"""

from django.db import close_old_connections, connection
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
import logging
import time

logger = logging.getLogger(__name__)


class DatabaseConnectionMiddleware(MiddlewareMixin):
    """
    Middleware to ensure database connections are properly managed and handle timeouts.
    
    This middleware:
    1. Closes old database connections before and after each request
    2. Monitors request processing time to help identify slow queries
    3. Ensures proper cleanup on exceptions
    """
    
    def process_request(self, request):
        """Close old connections and start timing before processing the request."""
        close_old_connections()
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Close old connections after processing the request and log slow requests."""
        processing_time = time.time() - getattr(request, '_start_time', time.time())
        
        if processing_time > 10:  # Log requests taking more than 10 seconds
            logger.warning(f"Slow request detected: {request.path} took {processing_time:.2f} seconds")
        
        close_old_connections()
        return response
    
    def process_exception(self, request, exception):
        """Close old connections if an exception occurs."""
        processing_time = time.time() - getattr(request, '_start_time', time.time())
        logger.error(f"Exception in request {request.path} after {processing_time:.2f} seconds: {str(exception)}")
        
        close_old_connections()
        return None
