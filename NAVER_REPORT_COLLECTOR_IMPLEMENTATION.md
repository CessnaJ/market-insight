# Naver Finance Report Collector Implementation

**Date**: 2026-02-22
**Status**: ✅ Completed

---

## Overview

This implementation adds Naver Finance report collection to the Market Insight system. Naver Finance reports are secondary sources with an authority weight of 0.4, complementing the primary sources (DART filings, earnings calls) with authority weight 1.0.

---

## Components Implemented

### 1. Naver Report Collector

**File**: [`backend/collector/naver_report_collector.py`](market-insight/backend/collector/naver_report_collector.py)

#### Key Classes and Functions

- **[`NaverReportCollector`](market-insight/backend/collector/naver_report_collector.py:48)**: Main class for collecting Naver Finance reports
  - [`collect_reports()`](market-insight/backend/collector/naver_report_collector.py:56): Collect reports for a given ticker
  - [`_extract_report_list()`](market-insight/backend/collector/naver_report_collector.py:95): Extract report list from Naver Finance page
  - [`_get_pdf_url()`](market-insight/backend/collector/naver_report_collector.py:168): Get PDF URL from report detail page
  - [`_extract_report_text()`](market-insight/backend/collector/naver_report_collector.py:197): Extract text from PDF using PyPDF2
  - [`_parse_date()`](market-insight/backend/collector/naver_report_collector.py:234): Parse date string
  - [`_parse_opinion()`](market-insight/backend/collector/naver_report_collector.py:258): Parse opinion (BUY/HOLD/SELL)
  - [`_parse_target_price()`](market-insight/backend/collector/naver_report_collector.py:277): Parse target price

- **[`NaverReport`](market-insight/backend/collector/naver_report_collector.py:20)**: Data class for Naver Finance report
  - Contains: ticker, company_name, title, analyst, brokerage, published_date, opinion, target_price, pdf_url, report_url, full_text

- **[`save_naver_report_to_db()`](market-insight/backend/collector/naver_report_collector.py:299)**: Save Naver report to database as PrimarySource

#### Features

- Playwright-based web scraping
- PDF download and text extraction
- Metadata parsing (analyst, opinion, target price)
- Authority weight: 0.4 (Secondary Source)

---

### 2. Naver Reports API

**File**: [`backend/api/routes/naver_reports.py`](market-insight/backend/api/routes/naver_reports.py)

#### Endpoints

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/naver-reports/collect` | Collect Naver reports (async background) |
| POST | `/api/v1/naver-reports/collect/sync` | Collect Naver reports (synchronous) |
| POST | `/api/v1/naver-reports/batch` | Collect reports for multiple tickers |
| GET | `/api/v1/naver-reports/list` | List collected Naver reports |
| GET | `/api/v1/naver-reports/{report_id}` | Get a specific Naver report |
| DELETE | `/api/v1/naver-reports/{report_id}` | Delete a Naver report |
| POST | `/api/v1/naver-reports/index/{report_id}` | Index a Naver report into parent-child chunks |
| POST | `/api/v1/naver-reports/index/batch` | Index multiple Naver reports |
| GET | `/api/v1/naver-reports/stats/summary` | Get statistics about collected reports |
| GET | `/api/v1/naver-reports/health` | Health check |

#### Request Models

```python
class NaverReportCollectionRequest(BaseModel):
    ticker: str  # Stock ticker (e.g., "005930")
    company_name: str  # Company name (e.g., "삼성전자")
    limit: int = 50  # Maximum number of reports
    headless: bool = True  # Browser headless mode
```

---

### 3. Parent-Child Indexing Integration

**File**: [`backend/analyzer/parent_child_indexer.py`](market-insight/backend/analyzer/parent_child_indexer.py)

#### Changes Made

- Added `"NAVER_REPORT": 0.4` to [`AUTHORITY_WEIGHTS`](market-insight/backend/analyzer/parent_child_indexer.py:39) dictionary
- Naver reports are now indexed with authority weight 0.4
- Parent-child chunking applies to Naver reports
- Naver reports are included in weighted search

---

### 4. API Registration

**File**: [`backend/api/main.py`](market-insight/backend/api/main.py)

#### Changes Made

- Added `naver_reports` to imports (line 62)
- Registered `naver_reports.router` (line 74)

---

### 5. Test Suite

**File**: [`backend/test_naver_reports.py`](market-insight/backend/test_naver_reports.py)

#### Test Classes

- **[`TestNaverReportCollector`](market-insight/backend/test_naver_reports.py:29)**: Test collector initialization and parsing
- **[`TestNaverReportStorage`](market-insight/backend/test_naver_reports.py:61)**: Test database storage
- **[`TestParentChildIndexing`](market-insight/backend/test_naver_reports.py:97)**: Test parent-child indexing
- **[`TestAuthorityWeight`](market-insight/backend/test_naver_reports.py:129)**: Test authority weight
- **[`TestNaverReportIntegration`](market-insight/backend/test_naver_reports.py:149)**: Integration tests

---

## API Usage Examples

### Collect Naver Reports (Async)

```bash
curl -X POST "http://localhost:8000/api/v1/naver-reports/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "005930",
    "company_name": "삼성전자",
    "limit": 20,
    "headless": true
  }'
```

### Collect Naver Reports (Sync)

```bash
curl -X POST "http://localhost:8000/api/v1/naver-reports/collect/sync" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "005930",
    "company_name": "삼성전자",
    "limit": 5
  }'
```

### Batch Collection

```bash
curl -X POST "http://localhost:8000/api/v1/naver-reports/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": [
      {"ticker": "005930", "company_name": "삼성전자"},
      {"ticker": "000660", "company_name": "SK하이닉스"}
    ],
    "limit_per_ticker": 10
  }'
```

### List Naver Reports

```bash
curl "http://localhost:8000/api/v1/naver-reports/list?ticker=005930&limit=10"
```

### Index Naver Reports

```bash
# Index a single report
curl -X POST "http://localhost:8000/api/v1/naver-reports/index/{report_id}"

# Index multiple reports
curl -X POST "http://localhost:8000/api/v1/naver-reports/index/batch?ticker=005930&limit=20"
```

### Get Statistics

```bash
curl "http://localhost:8000/api/v1/naver-reports/stats/summary?ticker=005930"
```

---

## Authority Weighting

| Source Type | Authority Weight | Description |
|-------------|------------------|-------------|
| EARNINGS_CALL | 1.0 | Primary source (management statements) |
| DART_FILING | 1.0 | Primary source (official disclosures) |
| IR_MATERIAL | 0.9 | Primary source (investor relations) |
| **NAVER_REPORT** | **0.4** | **Secondary source (analyst reports)** |
| REPORT | 0.4 | Secondary source (general reports) |

---

## Database Schema

Naver reports are stored in the [`PrimarySource`](market-insight/backend/storage/models.py:88) table with:

- `source_type = "NAVER_REPORT"`
- `authority_weight = 0.4`
- `extra_metadata` contains: analyst, brokerage, opinion, target_price, pdf_url, report_url

---

## Integration with Existing Components

### Weighted Search

Naver reports are included in weighted search with authority weight 0.4:

```python
# Weighted search automatically includes NAVER_REPORT
weighted_search = WeightedSearch()
results = weighted_search.search(
    query="삼성전자 HBM",
    source_types=["EARNINGS_CALL", "DART_FILING", "NAVER_REPORT"]
)
```

### Parent-Child Indexing

Naver reports are indexed with parent-child chunking:

```python
indexer = ParentChildIndexer()
result = indexer.index_primary_source(naver_report_id)
# Returns: summary_chunks, detail_chunks, chunk_ids
```

### Enhanced Report Builder

Naver reports are included in enhanced reports:

```python
builder = EnhancedReportBuilder()
report = await builder.generate_comprehensive_report(
    target_date=date.today(),
    tickers=["005930"]
)
# Includes NAVER_REPORT sources with authority weight 0.4
```

---

## Dependencies

### New Dependencies

- `playwright`: Web scraping
- `PyPDF2`: PDF text extraction

### Install

```bash
cd market-insight/backend
pip install playwright PyPDF2
playwright install chromium
```

---

## Testing

### Run Tests

```bash
cd market-insight/backend
pytest test_naver_reports.py -v -s
```

### Test Coverage

- Collector initialization
- Date parsing
- Opinion parsing
- Target price parsing
- Database storage
- Authority weight verification
- Parent-child indexing
- Integration tests (requires Naver Finance access)

---

## Known Limitations

1. **Naver Finance Anti-Scraping**: Naver Finance may implement anti-scraping measures. The implementation uses Playwright with stealth mode, but may need adjustments.

2. **PDF Availability**: Some reports may not have PDFs available. The implementation handles this gracefully.

3. **Rate Limiting**: Naver Finance may rate limit requests. Consider implementing delays between requests.

4. **Text Extraction Quality**: PDF text extraction may not be perfect for reports with complex layouts.

---

## Future Enhancements

1. **Retry Logic**: Add retry logic for failed downloads
2. **Scheduled Collection**: Add scheduled collection (daily/weekly)
3. **Incremental Updates**: Only collect new reports since last collection
4. **Proxy Support**: Add proxy support for anti-scraping
5. **Alternative Sources**: Add other Korean financial data sources (FnGuide, KIS)
6. **Report Quality Scoring**: Score reports based on analyst track record

---

## Summary

The Naver Finance Report Collector implementation completes the secondary source collection for the authority-weighted search system. Key achievements:

✅ Playwright-based web scraping
✅ PDF download and text extraction
✅ Metadata parsing (analyst, opinion, target price)
✅ Authority weight: 0.4 (Secondary Source)
✅ API endpoints for collection and management
✅ Parent-child indexing integration
✅ Weighted search integration
✅ Test suite

The system now has both primary sources (DART filings, earnings calls) and secondary sources (Naver reports) with proper authority weighting, enabling more comprehensive investment intelligence.
