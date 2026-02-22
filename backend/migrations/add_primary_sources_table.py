"""Database Migration: Add Primary Sources Table

This migration script adds the PrimarySource table to the database
for storing Korean securities data (DART filings, earnings calls, etc.)
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db import engine, init_database
from storage.models import PrimarySource


def migrate():
    """Run the migration"""
    print("Starting migration: Add Primary Sources Table...")
    
    # Initialize database tables
    init_database()
    
    print("✓ Migration completed successfully!")
    print("  - PrimarySource table created")
    print("  - Authority weight support (primary=1.0, secondary=0.4)")
    print("  - Source types: EARNINGS_CALL, DART_FILING, IR_MATERIAL")


if __name__ == "__main__":
    migrate()
