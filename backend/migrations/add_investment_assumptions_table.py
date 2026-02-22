"""Database Migration: Add Investment Assumptions Table (Sprint 3)

This migration script adds the InvestmentAssumption table to the database
for storing and tracking investment assumptions extracted from reports and filings.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db import engine, init_database
from storage.models import InvestmentAssumption


def migrate():
    """Run the migration"""
    print("Starting migration: Add Investment Assumptions Table (Sprint 3)...")
    
    # Initialize database tables
    init_database()
    
    print("✓ Migration completed successfully!")
    print("  - InvestmentAssumption table created")
    print("  - Assumption categories: REVENUE, MARGIN, MACRO, CAPACITY, MARKET_SHARE")
    print("  - Time horizons: SHORT, MEDIUM, LONG")
    print("  - Validation status tracking: PENDING, VERIFIED, FAILED")
    print("  - Confidence score support (0.0-1.0)")
    print("  - Authority weight adjustment based on source type")


if __name__ == "__main__":
    migrate()
