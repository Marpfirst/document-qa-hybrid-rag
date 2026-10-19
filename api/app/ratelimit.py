"""Shared rate limiter.

Lives in its own module so route modules can decorate handlers without
importing `main` (which imports them back).

Rate limits are the layer that actually stops scripted abuse. CORS does not —
`curl` ignores it entirely — so this plus a bot check is what protects the
free-tier quota from a public demo link.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
