# streamlit_app.py
"""Main entry point for Streamlit app."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ui import app

if __name__ == "__main__":
    app  # Import triggers Streamlit execution
