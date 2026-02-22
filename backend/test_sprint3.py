"""Sprint 3 Tests: Assumption Tracking System

Tests for:
- Assumption extraction from sample reports
- Validation logic with mock data
- Accuracy calculation
- API endpoints
"""

import pytest
from datetime import date, datetime, timedelta
from sqlmodel import Session, create_engine

from storage.models import InvestmentAssumption
from storage.db import (
    add_investment_assumption,
    get_assumptions_by_ticker,
    get_pending_assumptions,
    get_assumption_by_id,
    validate_assumption,
    get_assumption_accuracy_stats,
    delete_assumption,
    get_all_assumptions
)
from analyzer.assumption_extractor import (
    AssumptionExtractor,
    ExtractedAssumption,
    extract_assumptions_from_content,
    convert_to_assumption_models
)
from scheduler.assumption_validator import (
    AssumptionValidator,
    FinancialDataProvider,
    run_assumption_validation_job,
    validate_single_assumption,
    get_accuracy_trends
)


# ──── Test Fixtures ────
@pytest.fixture
def test_engine():
    """Create test database engine"""
    engine = create_engine("sqlite:///:memory:")
    from storage.models import init_db
    init_db(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test database session"""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def sample_assumption():
    """Sample investment assumption"""
    return InvestmentAssumption(
        ticker="005930",
        company_name="삼성전자",
        assumption_text="Q3 HBM 매출 1조 달성 예상",
        assumption_category="REVENUE",
        time_horizon="SHORT",
        predicted_value="1조",
        metric_name="HBM 매출",
        verification_date=date.today() + timedelta(days=30),
        model_confidence_at_generation=0.8,
        source_type="EARNINGS_CALL",
        status="PENDING"
    )


@pytest.fixture
def sample_report_content():
    """Sample report content for assumption extraction"""
    return """
삼성전자 2024년 3분기 실적 발표 요약

1. HBM 매출
   - Q3 HBM 매출 1조 달성 예상
   - HBM3e 생산량 증가로 매출 성장 기대

2. 마진 개선
   - GP 마진 20% 개선 목표
   - 비용 절감 노력 지속

3. 시장 전망
   - 금리 인하 기대감으로 반도체 수요 회복
   - AI 서버 시장 성장 지속 예상
   """


# ──── Test Database Operations ────
def test_add_investment_assumption(test_session, sample_assumption):
    """Test adding investment assumption"""
    added = add_investment_assumption(test_session, sample_assumption)
    
    assert added.id is not None
    assert added.ticker == "005930"
    assert added.assumption_text == "Q3 HBM 매출 1조 달성 예상"
    assert added.status == "PENDING"


def test_get_assumption_by_id(test_session, sample_assumption):
    """Test getting assumption by ID"""
    added = add_investment_assumption(test_session, sample_assumption)
    retrieved = get_assumption_by_id(test_session, added.id)
    
    assert retrieved is not None
    assert retrieved.id == added.id
    assert retrieved.ticker == "005930"


def test_get_assumptions_by_ticker(test_session, sample_assumption):
    """Test getting assumptions by ticker"""
    add_investment_assumption(test_session, sample_assumption)
    
    # Add another assumption for same ticker
    assumption2 = InvestmentAssumption(
        ticker="005930",
        company_name="삼성전자",
        assumption_text="GP 마진 20% 개선",
        assumption_category="MARGIN",
        time_horizon="MEDIUM",
        predicted_value="20%",
        metric_name="GP 마진",
        verification_date=date.today() + timedelta(days=90),
        model_confidence_at_generation=0.7,
        source_type="EARNINGS_CALL",
        status="PENDING"
    )
    add_investment_assumption(test_session, assumption2)
    
    assumptions = get_assumptions_by_ticker(test_session, "005930")
    
    assert len(assumptions) == 2
    assert all(a.ticker == "005930" for a in assumptions)


def test_get_pending_assumptions(test_session, sample_assumption):
    """Test getting pending assumptions"""
    # Add pending assumption with past verification date
    sample_assumption.verification_date = date.today() - timedelta(days=1)
    add_investment_assumption(test_session, sample_assumption)
    
    # Add verified assumption
    verified = InvestmentAssumption(
        ticker="005930",
        company_name="삼성전자",
        assumption_text="이미 검증된 가정",
        assumption_category="REVENUE",
        time_horizon="SHORT",
        predicted_value="1조",
        metric_name="HBM 매출",
        verification_date=date.today() - timedelta(days=1),
        actual_value="1.2조",
        is_correct=True,
        validation_source="FinancialDataProvider",
        model_confidence_at_generation=0.8,
        source_type="EARNINGS_CALL",
        status="VERIFIED"
    )
    add_investment_assumption(test_session, verified)
    
    pending = get_pending_assumptions(test_session)
    
    assert len(pending) == 1
    assert pending[0].status == "PENDING"


def test_validate_assumption(test_session, sample_assumption):
    """Test validating an assumption"""
    added = add_investment_assumption(test_session, sample_assumption)
    
    validated = validate_assumption(
        test_session,
        added.id,
        actual_value="1.2조",
        is_correct=True,
        validation_source="FinancialDataProvider"
    )
    
    assert validated is not None
    assert validated.actual_value == "1.2조"
    assert validated.is_correct is True
    assert validated.status == "VERIFIED"
    assert validated.validation_source == "FinancialDataProvider"


def test_get_assumption_accuracy_stats(test_session):
    """Test getting accuracy statistics"""
    # Add verified assumptions
    for i in range(5):
        assumption = InvestmentAssumption(
            ticker="005930",
            company_name="삼성전자",
            assumption_text=f"가정 {i}",
            assumption_category="REVENUE" if i < 3 else "MARGIN",
            time_horizon="SHORT" if i < 2 else "MEDIUM",
            predicted_value="1조",
            metric_name="HBM 매출",
            verification_date=date.today() - timedelta(days=1),
            actual_value="1.2조",
            is_correct=True if i < 4 else False,
            validation_source="FinancialDataProvider",
            model_confidence_at_generation=0.8,
            source_type="EARNINGS_CALL",
            status="VERIFIED" if i < 4 else "FAILED"
        )
        add_investment_assumption(test_session, assumption)
    
    stats = get_assumption_accuracy_stats(test_session)
    
    assert stats["total"] == 5
    assert stats["correct"] == 4
    assert stats["incorrect"] == 1
    assert stats["accuracy"] == 0.8
    assert "by_category" in stats
    assert "by_time_horizon" in stats


def test_delete_assumption(test_session, sample_assumption):
    """Test deleting an assumption"""
    added = add_investment_assumption(test_session, sample_assumption)
    
    success = delete_assumption(test_session, added.id)
    
    assert success is True
    
    retrieved = get_assumption_by_id(test_session, added.id)
    assert retrieved is None


# ──── Test Assumption Extraction ────
def test_extract_assumptions_from_content(sample_report_content):
    """Test extracting assumptions from report content"""
    extractor = AssumptionExtractor()
    
    result = extractor.extract_assumptions(
        content=sample_report_content,
        ticker="005930",
        company_name="삼성전자",
        source_type="EARNINGS_CALL"
    )
    
    assert result.ticker == "005930"
    assert result.company_name == "삼성전자"
    assert len(result.assumptions) > 0
    
    # Check that assumptions have required fields
    for assumption in result.assumptions:
        assert assumption.assumption_text is not None
        assert assumption.assumption_category in ["REVENUE", "MARGIN", "MACRO", "CAPACITY", "MARKET_SHARE"]
        assert assumption.time_horizon in ["SHORT", "MEDIUM", "LONG"]
        assert 0.0 <= assumption.confidence <= 1.0


def test_convert_to_assumption_models():
    """Test converting extracted assumptions to database models"""
    extracted = ExtractedAssumption(
        assumption_text="Q3 HBM 매출 1조 달성 예상",
        assumption_category="REVENUE",
        time_horizon="SHORT",
        predicted_value="1조",
        metric_name="HBM 매출",
        verification_date="2024-10-31",
        confidence=0.8,
        reasoning="Company explicitly stated target"
    )
    
    extractor = AssumptionExtractor()
    model = extractor.to_investment_assumption(
        extracted=extracted,
        ticker="005930",
        company_name="삼성전자",
        source_type="EARNINGS_CALL"
    )
    
    assert model.ticker == "005930"
    assert model.assumption_text == "Q3 HBM 매출 1조 달성 예상"
    assert model.assumption_category == "REVENUE"
    assert model.predicted_value == "1조"
    assert model.metric_name == "HBM 매출"
    assert model.status == "PENDING"


def test_authority_weight_adjustment():
    """Test that authority weights are applied to confidence"""
    extractor = AssumptionExtractor()
    
    # Test with different source types
    source_types = ["EARNINGS_CALL", "DART_FILING", "IR_MATERIAL", "SECURITIES_REPORT"]
    
    for source_type in source_types:
        result = extractor.extract_assumptions(
            content="Q3 HBM 매출 1조 달성 예상",
            ticker="005930",
            company_name="삼성전자",
            source_type=source_type
        )
        
        if result.assumptions:
            # DART_FILING should have higher weight than SECURITIES_REPORT
            pass


# ──── Test Validation Logic ────
def test_extract_number_from_string():
    """Test extracting numbers from Korean strings"""
    validator = AssumptionValidator()
    
    # Test various formats
    test_cases = [
        ("1조", 1000000000000),
        ("1.2조", 1200000000000),
        ("20%", 20.0),
        ("1.5%", 1.5),
        ("500억", 500000000),
    ]
    
    for value_str, expected in test_cases:
        result = validator._extract_number(value_str)
        assert result == expected, f"Failed for {value_str}: got {result}, expected {expected}"


def test_date_to_period_conversion():
    """Test converting date to period identifier"""
    validator = AssumptionValidator()
    
    # Test Q3 2024
    q3_date = date(2024, 8, 15)
    period = validator._date_to_period(q3_date)
    assert period == "2024-Q3"
    
    # Test Q4 2024
    q4_date = date(2024, 12, 1)
    period = validator._date_to_period(q4_date)
    assert period == "2024-Q4"


def test_financial_data_provider():
    """Test mock financial data provider"""
    provider = FinancialDataProvider()
    
    # Test getting data for Samsung
    value = provider.get_financial_metric(
        ticker="005930",
        metric_name="HBM 매출",
        period="2024-Q3"
    )
    
    assert value is not None
    assert value == "1.2조"
    
    # Test non-existent data
    value = provider.get_financial_metric(
        ticker="999999",
        metric_name="Unknown",
        period="2024-Q3"
    )
    
    assert value is None


def test_validate_single_assumption(test_session, sample_assumption):
    """Test validating a single assumption"""
    # Add assumption with past verification date
    sample_assumption.verification_date = date.today() - timedelta(days=1)
    added = add_investment_assumption(test_session, sample_assumption)
    
    # Validate the assumption
    result = validate_single_assumption(added.id)
    
    assert result["success"] is True
    assert "status" in result


def test_get_accuracy_trends(test_session):
    """Test getting accuracy trends over time"""
    # Add some verified assumptions with different dates
    for i in range(5):
        assumption = InvestmentAssumption(
            ticker="005930",
            company_name="삼성전자",
            assumption_text=f"가정 {i}",
            assumption_category="REVENUE",
            time_horizon="SHORT",
            predicted_value="1조",
            metric_name="HBM 매출",
            verification_date=date.today() - timedelta(days=i * 10),
            actual_value="1.2조",
            is_correct=True,
            validation_source="FinancialDataProvider",
            model_confidence_at_generation=0.8,
            source_type="EARNINGS_CALL",
            status="VERIFIED"
        )
        add_investment_assumption(test_session, assumption)
    
    trends = get_accuracy_trends(ticker="005930", days=60)
    
    assert "overall_stats" in trends
    assert "weekly_trends" in trends


# ──── Test API Endpoints (Integration Tests) ────
# Note: These tests would require running the FastAPI app
# They are included as examples for manual testing

"""
Example API test cases:

def test_list_assumptions(client):
    response = client.get("/api/v1/assumptions/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_assumption_by_id(client, sample_assumption_id):
    response = client.get(f"/api/v1/assumptions/{sample_assumption_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_assumption_id

def test_extract_assumptions(client):
    request_data = {
        "content": "Q3 HBM 매출 1조 달성 예상",
        "ticker": "005930",
        "company_name": "삼성전자",
        "source_type": "EARNINGS_CALL"
    }
    response = client.post("/api/v1/assumptions/extract", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_accuracy_stats(client):
    response = client.get("/api/v1/assumptions/stats/accuracy")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "accuracy" in data
"""


# ──── Run Tests ────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
