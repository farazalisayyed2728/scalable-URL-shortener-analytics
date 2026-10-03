import time
from typing import Any, Dict, Tuple
from django.db import connection
from apps.links.services.cache import get_redis_client


def check_database() -> Tuple[bool, float, str]:
    """
    Executes a minimal query against PostgreSQL with execution time measurement.
    Returns: (is_healthy, latency_ms, detail_message)
    """
    start_time = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
            if row and row[0] == 1:
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                return True, latency, "Database connection operational."
            return False, 0.0, "Unexpected database query response."
    except Exception as exc:
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return False, latency, f"Database unreachable: {str(exc)}"


def check_redis() -> Tuple[bool, float, str]:
    """
    Sends a PING command to Redis with execution time measurement.
    Returns: (is_healthy, latency_ms, detail_message)
    """
    start_time = time.perf_counter()
    try:
        client = get_redis_client()
        # Redis PING responds with boolean True or b"PONG"
        if client.ping():
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            return True, latency, "Redis connection operational."
        return False, 0.0, "Redis ping failed."
    except Exception as exc:
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return False, latency, f"Redis unreachable: {str(exc)}"


def get_system_health() -> Tuple[bool, Dict[str, Any]]:
    """
    Aggregates health across all downstream dependencies.
    """
    db_healthy, db_latency, db_msg = check_database()
    redis_healthy, redis_latency, redis_msg = check_redis()

    is_overall_healthy = db_healthy and redis_healthy

    payload = {
        "status": "healthy" if is_overall_healthy else "unhealthy",
        "dependencies": {
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "latency_ms": db_latency,
                "detail": db_msg,
            },
            "redis": {
                "status": "healthy" if redis_healthy else "unhealthy",
                "latency_ms": redis_latency,
                "detail": redis_msg,
            },
        },
    }
    return is_overall_healthy, payload