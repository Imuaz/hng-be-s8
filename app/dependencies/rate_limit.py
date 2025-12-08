"""
Simple in-memory rate limiter dependency.
"""

from fastapi import Request, HTTPException, status
from typing import Dict, List
import time


class RateLimiter:
    """
    Simple in-memory rate limiter using a sliding window.
    NOTE: This is per-worker. For production with multiple workers, use Redis.
    """

    def __init__(self, requests_limit: int = 10, time_window: int = 60):
        self.requests_limit = requests_limit
        self.time_window = time_window  # in seconds
        self.requests: Dict[str, List[float]] = {}

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Initialize if not exists
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Filter out old requests (sliding window)
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if current_time - t < self.time_window
        ]

        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.requests_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        # Record new request
        self.requests[client_ip].append(current_time)
