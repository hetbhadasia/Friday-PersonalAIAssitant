"""
F.R.I.D.A.Y. Config Package
Backward-compatible re-export of the config singleton.
"""

from friday.config.settings import config, FridayConfig

__all__ = ["config", "FridayConfig"]
