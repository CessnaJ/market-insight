"""Database Migration: Add Price Attributions Table

This migration script adds the PriceAttribution table to the database
for storing temporal signal decomposition analysis results.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db import engine, init_database
from storage.models import PriceAttribution


def migrate():
    """Run the migration"""
    print("Starting migration: Add Price Attributions Table...")
    
    # Initialize database tables
    init_database()
    
    print("✓ Migration completed successfully!")
    print("  - PriceAttribution table created")
    print("  - Temporal breakdown support (short/medium/long-term)")
    print("  - AI analysis summary storage")
    print("  - Confidence score tracking")
    print("  - Dominant timeframe identification")


if __name__ == "__main__":
    migrate()
