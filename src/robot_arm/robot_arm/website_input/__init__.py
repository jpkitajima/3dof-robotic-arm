"""Website input bridge for the robot arm.

This module hosts a small local web UI and a websocket endpoint that can be used
as an alternate input device (virtual controller).
"""

from .website_input import WebsiteInput

__all__ = [
    'WebsiteInput',
]
