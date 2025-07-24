"""
Custom middleware for handling database connections in gevent environments.
"""

from django.db import close_old_connections
from django.utils.deprecation import MiddlewareMixin


class GeventDatabaseMiddleware(MiddlewareMixin):
    """
    Middleware to ensure database connections are properly managed in gevent environments.
    
    This middleware closes old database connections before and after each request
    to prevent thread-safety issues that can occur when using gevent workers.
    """
    
    def process_request(self, request):
        """Close old connections before processing the request."""
        close_old_connections()
        return None
    
    def process_response(self, request, response):
        """Close old connections after processing the request."""
        close_old_connections()
        return response
    
    def process_exception(self, request, exception):
        """Close old connections if an exception occurs."""
        close_old_connections()
        return None
