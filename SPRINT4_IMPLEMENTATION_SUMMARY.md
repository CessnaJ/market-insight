# Sprint 4 Implementation Summary: Parent-Child Indexing & Search

**Date**: 2026-02-22  
**Status**: ✅ Completed

---

## Overview

Sprint 4 implements advanced search functionality with parent-child chunking, authority-weighted ranking, and hybrid search capabilities. The system now prioritizes primary sources (DART filings, earnings calls) over secondary sources (reports) in search results.

---

## Implemented Components

### 1. Database Schema

**File**: [`market-insight/backend/storage/models.py`](market-insight/backend/storage/models.py:145)

Added `ReportChunk` model with parent-child structure:

```python
class ReportChunk(SQLModel, table=True):
    id: str
    source_id: str  # References reports.id OR primary_sources.id
    source_type: str  # 'REPORT' or 'PRIMARY'
    content: str  # Chunk text content
    embedding: str  # pgvector stored as string
    authority_weight: float  # Primary=1.0, Report=0.4
    chunk_type: str  # 'SUMMARY' or 'DETAIL'
    chunk_index: int  # Order within chunks
    parent_id: Optional[str]  # For DETAIL chunks
    created_at: datetime
    updated_at: datetime
```

**Migration**: [`market-insight/backend/migrations/add_report_chunks_table.py`](market-insight/backend/migrations/add_report_chunks_table.py)

---

### 2. Parent-Child Indexer

**File**: [`market-insight/backend/analyzer/parent_child_indexer.py`](market-insight/backend/analyzer/parent_child_indexer.py)

Implements two-level chunking strategy:

- **Level 1 (SUMMARY)**: 2-3 sentences, broad topics
- **Level 2 (DETAIL)**: Single sentences, specific claims with parent context

**Key Features**:
- `index_report()`: Index daily reports into chunks
- `index_primary_source()`: Index primary sources (DART, earnings calls)
- Parent context preservation for detail chunks
- Automatic embedding generation using LLM router

**Authority Weights**:
```python
AUTHORITY_WEIGHTS = {
    "EARNINGS_CALL": 1.0,
    "DART_FILING": 1.0,
    "IR_MATERIAL": 0.9,
    "REPORT": 0.4,  # Secondary source
}
```

---

### 3. Weighted Search

**File**: [`market-insight/backend/analyzer/weighted_search.py`](market-insight/backend/analyzer/weighted_search.py)

Implements hybrid search combining:

**Formula**: `score = (similarity * authority_weight) + keyword_bonus`

**Key Features**:
- Vector similarity search using pgvector
- Authority weight multiplication for primary sources
- Keyword bonus for exact matches
- Parent context retrieval
- Comparison of weighted vs unweighted results

**Methods**:
- `search()`: Basic weighted search
- `search_with_parent_context()`: Search with full parent and sibling chunks
- `compare_search_results()`: Compare weighted vs unweighted rankings

---

### 4. Database Operations

**File**: [`market-insight/backend/storage/db.py`](market-insight/backend/storage/db.py:503)

Added chunk-related operations:

- `add_report_chunk()`: Add a single chunk
- `get_chunks_by_source()`: Get all chunks for a source
- `get_chunks_with_parent_context()`: Get chunk with parent and siblings
- `get_parent_chunks()`: Get all parent (summary) chunks
- `search_chunks_weighted()`: Database-level weighted search
- `delete_chunks_by_source()`: Delete all chunks for a source
- `get_chunk_statistics()`: Get chunk statistics

---

### 5. API Endpoints

**File**: [`market-insight/backend/api/routes/search.py`](market-insight/backend/api/routes/search.py)

**Endpoints**:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/search/` | Weighted search with filters |
| POST | `/api/v1/search/with-context` | Search with parent context |
| GET | `/api/v1/search/chunks/{id}` | Get chunk with parent context |
| GET | `/api/v1/search/parent/{id}` | Get parent chunks for source |
| POST | `/api/v1/search/reindex/report/{id}` | Reindex a report |
| POST | `/api/v1/search/reindex/primary/{id}` | Reindex a primary source |
| GET | `/api/v1/search/compare` | Compare weighted vs unweighted |
| GET | `/api/v1/search/statistics` | Get chunk statistics |

**Request Model**:
```python
class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    source_type_filter: Optional[str]  # 'REPORT' or 'PRIMARY'
    chunk_type_filter: Optional[str]  # 'SUMMARY' or 'DETAIL'
    keyword_bonus: float = 0.1
    min_similarity: float = 0.0
```

---

### 6. Integration

**Updated**: [`market-insight/backend/api/main.py`](market-insight/backend/api/main.py:62)

Added search router to main API:
```python
from api.routes import ..., search
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
```

---

### 7. Testing

**File**: [`market-insight/backend/test_sprint4.py`](market-insight/backend/test_sprint4.py)

Comprehensive test suite covering:

- **Parent-Child Chunking Tests**:
  - `test_parent_child_chunking_primary_source()`
  - `test_parent_child_chunking_report()`
  - `test_authority_weights()`

- **Weighted Search Tests**:
  - `test_weighted_search_primary_sources_rank_higher()`
  - `test_weighted_search_formula()`
  - `test_hybrid_search()`
  - `test_search_with_parent_context()`

- **Database Operations Tests**:
  - `test_get_chunks_with_parent_context()`
  - `test_get_parent_chunks()`
  - `test_get_chunk_statistics()`

- **Search Quality Tests**:
  - `test_compare_search_results()`
  - `test_search_filters()`

- **Edge Cases**:
  - `test_empty_content_chunking()`
  - `test_reindexing()`

- **Real Data Tests (삼성전자)**:
  - `test_samsung_hbm_search()`
  - `test_samsung_authority_weighting()`

---

## Expected Outcomes Achieved

### ✅ 1. Primary Sources Rank Higher

Primary sources (DART_FILING, EARNINGS_CALL) now appear first in search results due to:
- Higher authority weights (1.0 vs 0.4)
- Weighted score formula prioritizes primary sources

### ✅ 2. Parent Context Preservation

- Detail chunks include parent_id linking to summary chunks
- API endpoint returns full parent context
- Sibling chunks available for complete context

### ✅ 3. Summary Chunks for Broad Topics

- Summary chunks (2-3 sentences) provide topic overviews
- Easy to browse high-level information
- Detail chunks available for specific claims

### ✅ 4. Improved Search Quality

- Authority weighting improves result relevance
- Hybrid search combines semantic and exact matching
- Keyword bonus for exact phrase matches

### ✅ 5. Hybrid Search Implementation

- Vector similarity for semantic search
- Keyword filtering for exact matches
- Combined scoring for best results

---

## Usage Examples

### Index a Primary Source

```python
from analyzer.parent_child_indexer import index_primary_source

result = index_primary_source(primary_source_id)
# Returns: {"source_id": "...", "total_chunks": 15, "summary_chunks": 5, "detail_chunks": 10}
```

### Perform Weighted Search

```python
from analyzer.weighted_search import search

results = search(
    query="삼성전자 HBM 매출",
    limit=10,
    source_type_filter="PRIMARY",
    keyword_bonus=0.2
)
# Results sorted by weighted_score
```

### Search with Parent Context

```python
from analyzer.weighted_search import WeightedSearch

search_engine = WeightedSearch()
results = search_engine.search_with_parent_context(
    query="HBM",
    limit=5,
    include_siblings=True
)
# Returns parent chunks with all detail chunks
```

### API Usage

```bash
# Weighted search
POST /api/v1/search/
{
  "query": "삼성전자 HBM",
  "limit": 10,
  "source_type_filter": "PRIMARY",
  "keyword_bonus": 0.2
}

# Get chunk with parent context
GET /api/v1/search/chunks/{chunk_id}?include_siblings=true

# Reindex a source
POST /api/v1/search/reindex/primary/{source_id}
```

---

## Database Schema

### report_chunks Table

```sql
CREATE TABLE report_chunks (
    id VARCHAR(36) PRIMARY KEY,
    source_id VARCHAR(36) NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    authority_weight FLOAT DEFAULT 1.0,
    chunk_type VARCHAR(20) NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    parent_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_report_chunks_source_id ON report_chunks(source_id);
CREATE INDEX idx_report_chunks_source_type ON report_chunks(source_type);
CREATE INDEX idx_report_chunks_chunk_type ON report_chunks(chunk_type);
CREATE INDEX idx_report_chunks_parent_id ON report_chunks(parent_id);
CREATE INDEX idx_report_chunks_embedding ON report_chunks USING ivfflat (embedding vector_cosine_ops);
```

---

## Running the Migration

```bash
cd market-insight/backend
python migrations/add_report_chunks_table.py
```

To rollback:
```bash
python migrations/add_report_chunks_table.py rollback
```

---

## Running Tests

```bash
cd market-insight/backend
pytest test_sprint4.py -v
```

---

## Integration with Existing Components

### LLM Router
- Uses existing [`get_embedding()`](market-insight/backend/analyzer/llm_router.py:173) function
- Compatible with Ollama nomic-embed-text model

### Vector Store
- Integrates with existing pgvector setup
- Uses PostgreSQL for vector storage and search

### Report Builder
- Can be extended to auto-index generated reports
- Seamless integration with existing workflow

---

## Performance Considerations

1. **Vector Index**: Uses ivfflat index for fast similarity search
2. **Chunking**: Two-level structure reduces embedding count
3. **Caching**: Parent context cached in database
4. **Batch Operations**: Supports batch indexing for efficiency

---

## Future Enhancements

1. **Auto-indexing**: Automatically index new reports and primary sources
2. **Chunk Size Tuning**: Optimize chunk sizes based on content type
3. **Relevance Feedback**: Learn from user clicks to improve ranking
4. **Cross-lingual Search**: Support Korean and English queries
5. **Faceted Search**: Add filters by date, ticker, source type

---

## Success Criteria Met

| Criteria | Status |
|----------|--------|
| Primary sources rank higher than secondary sources | ✅ |
| Hybrid search improves relevance | ✅ |
| Parent-child context is preserved | ✅ |
| Search performance is acceptable | ✅ |
| Comprehensive test coverage | ✅ |

---

## Files Created/Modified

### Created:
- [`market-insight/backend/analyzer/parent_child_indexer.py`](market-insight/backend/analyzer/parent_child_indexer.py)
- [`market-insight/backend/analyzer/weighted_search.py`](market-insight/backend/analyzer/weighted_search.py)
- [`market-insight/backend/api/routes/search.py`](market-insight/backend/api/routes/search.py)
- [`market-insight/backend/migrations/add_report_chunks_table.py`](market-insight/backend/migrations/add_report_chunks_table.py)
- [`market-insight/backend/test_sprint4.py`](market-insight/backend/test_sprint4.py)
- [`market-insight/SPRINT4_IMPLEMENTATION_SUMMARY.md`](market-insight/SPRINT4_IMPLEMENTATION_SUMMARY.md)

### Modified:
- [`market-insight/backend/storage/models.py`](market-insight/backend/storage/models.py) - Added ReportChunk model
- [`market-insight/backend/storage/db.py`](market-insight/backend/storage/db.py) - Added chunk operations
- [`market-insight/backend/api/main.py`](market-insight/backend/api/main.py) - Added search router

---

## Next Steps

Proceed to **Sprint 5: Integration & Polish** to:
1. Integrate all components into existing report builder
2. Update dashboard to show search results
3. Add auto-indexing for new content
4. Performance optimization
5. User documentation
