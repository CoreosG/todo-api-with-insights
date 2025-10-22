"""
Lambda entry point that imports from the src package.
This allows the relative imports within src to work properly.
"""

import sys
from pathlib import Path

# Get the api directory (parent of src)
api_dir = Path(__file__).parent

# Add the api directory to Python path
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

# Now we can import from src as a subpackage
from src.main import app, handler

def lambda_handler(event, context):
    """Lambda handler function that delegates to the FastAPI handler."""
    return handler(event, context)