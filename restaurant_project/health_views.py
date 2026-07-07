import logging
from django.http import JsonResponse
from django.db import connection

logger = logging.getLogger(__name__)

def health_check(request):
    """
    Liveness Check: Returns HTTP 200 if the application process is running.
    No database calls or authentication required.
    """
    response = JsonResponse({"status": "ok"})
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

def readiness_check(request):
    """
    Readiness Check: Verifies the application is ready to serve database-dependent traffic.
    Performs a lightweight 'SELECT 1' database query.
    Returns HTTP 200 if database works, and HTTP 503 Service Unavailable if it fails.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
        
        response = JsonResponse({"status": "ready", "database": "ok"})
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
    except Exception as e:
        logger.error(f"Readiness check failed: Database connection error: {e}")
        response = JsonResponse(
            {"status": "unavailable", "database": "error"},
            status=503
        )
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
