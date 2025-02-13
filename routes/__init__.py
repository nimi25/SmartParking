from flask import Blueprint

# Ensure `parking_bp` is imported properly
from routes.parking import parking_bp  # Using relative import

# Expose it for imports
__all__ = ["parking_bp"]
