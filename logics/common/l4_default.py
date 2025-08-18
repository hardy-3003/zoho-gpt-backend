"""
Default L4 singleton adapter

Provides a thin convenience instance with the same deterministic
no-op behavior as the L4 base. Useful for immediate wiring.
"""

from .l4_base import L4Base


class _L4Default(L4Base):
    pass


L4_DEFAULT = _L4Default()

__all__ = ["L4_DEFAULT", "_L4Default"]
