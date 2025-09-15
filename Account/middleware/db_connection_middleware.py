from django.db import close_old_connections

class DBConnectionMiddleware:
    """
    Ensures DB connections are valid for every request.
    Prevents 'MySQL Connection not available' errors in Gunicorn.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        close_old_connections()   # Close stale connections before handling
        response = self.get_response(request)
        close_old_connections()   # Clean up after response
        return response
