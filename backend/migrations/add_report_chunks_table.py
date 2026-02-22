"""Migration: Add report_chunks table for Sprint 4

This migration creates the report_chunks table for parent-child indexing
and weighted search functionality.
"""

from sqlalchemy import text
from storage.db import engine


def migrate():
    """Create report_chunks table with pgvector support"""
    
    # First, ensure pgvector extension is enabled
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    
    # Create report_chunks table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS report_chunks (
        id VARCHAR(36) PRIMARY KEY,
        source_id VARCHAR(36) NOT NULL,
        source_type VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        embedding vector(768),  -- Ollama nomic-embed-text uses 768 dimensions
        authority_weight FLOAT DEFAULT 1.0,
        chunk_type VARCHAR(20) NOT NULL,
        chunk_index INTEGER DEFAULT 0,
        parent_id VARCHAR(36),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Create indexes for better query performance
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_report_chunks_source_id ON report_chunks(source_id);",
        "CREATE INDEX IF NOT EXISTS idx_report_chunks_source_type ON report_chunks(source_type);",
        "CREATE INDEX IF NOT EXISTS idx_report_chunks_chunk_type ON report_chunks(chunk_type);",
        "CREATE INDEX IF NOT EXISTS idx_report_chunks_parent_id ON report_chunks(parent_id);",
        "CREATE INDEX IF NOT EXISTS idx_report_chunks_authority_weight ON report_chunks(authority_weight);",
    ]
    
    # Create vector index for similarity search
    create_vector_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_report_chunks_embedding 
    ON report_chunks USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
    """
    
    with engine.connect() as conn:
        # Create table
        conn.execute(text(create_table_sql))
        conn.commit()
        print("✓ Created report_chunks table")
        
        # Create indexes
        for index_sql in create_indexes_sql:
            conn.execute(text(index_sql))
            conn.commit()
        print("✓ Created report_chunks indexes")
        
        # Create vector index
        try:
            conn.execute(text(create_vector_index_sql))
            conn.commit()
            print("✓ Created vector similarity index")
        except Exception as e:
            print(f"⚠ Warning: Could not create vector index: {e}")
            print("  Vector index may need to be created after data is populated")
    
    print("\n✅ Migration completed successfully!")


def rollback():
    """Rollback migration - drop report_chunks table"""
    drop_table_sql = "DROP TABLE IF EXISTS report_chunks CASCADE;"
    
    with engine.connect() as conn:
        conn.execute(text(drop_table_sql))
        conn.commit()
        print("✓ Dropped report_chunks table")
    
    print("\n✅ Rollback completed successfully!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()
