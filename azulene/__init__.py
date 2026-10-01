"""Small, dependency-light 2D drawing helpers.

The package deliberately exposes its two public namespaces so code can use
``azulene.math`` and ``azulene.drawing`` directly after importing azulene.
"""

from . import drawing, math

__all__ = ["drawing", "math"]

