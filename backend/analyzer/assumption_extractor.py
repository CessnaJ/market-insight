"""Assumption Extractor - Extract investment assumptions from reports and filings

This module uses LLM to extract key investment assumptions from:
- Earnings calls
- DART filings
- IR materials
- Securities reports

Assumption categories:
- REVENUE: Sales/revenue assumptions (e.g., "Q3 HBM 매출 1조 달성")
- MARGIN: Margin/profitability assumptions (e.g., "GP 마진 20% 개선")
- MACRO: Macro environment assumptions (e.g., "금리 인하")
- CAPACITY: Production capacity assumptions
- MARKET_SHARE: Market share assumptions
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field

from analyzer.llm_router import LLMRouter, get_llm_router
from storage.models import InvestmentAssumption

logger = logging.getLogger(__name__)


# ──── Data Models ────
class ExtractedAssumption(BaseModel):
    """Extracted assumption from LLM"""
    assumption_text: str = Field(description="The assumption text")
    assumption_category: str = Field(description="Category: REVENUE, MARGIN, MACRO, CAPACITY, MARKET_SHARE")
    time_horizon: str = Field(description="Time horizon: SHORT, MEDIUM, LONG")
    predicted_value: Optional[str] = Field(default=None, description="Predicted value (e.g., '1조', '20%')")
    metric_name: Optional[str] = Field(default=None, description="Metric name (e.g., 'HBM 매출', 'GP 마진')")
    verification_date: Optional[str] = Field(default=None, description="Date when assumption can be verified (YYYY-MM-DD)")
    confidence: float = Field(default=0.5, description="Confidence score (0.0-1.0)")
    reasoning: Optional[str] = Field(default=None, description="Reasoning for the assumption")


class AssumptionExtractionResult(BaseModel):
    """Result of assumption extraction"""
    assumptions: List[ExtractedAssumption] = Field(default_factory=list)
    ticker: str
    company_name: Optional[str] = None
    source_type: str
    source_id: Optional[str] = None


# ──── Assumption Extractor ────
class AssumptionExtractor:
    """
    Extract investment assumptions from reports and filings using LLM
    
    Usage:
        extractor = AssumptionExtractor()
        result = extractor.extract_assumptions(
            content="Q3 HBM 매출 1조 달성 예상...",
            ticker="005930",
            company_name="삼성전자",
            source_type="EARNINGS_CALL"
        )
    """
    
    # Authority weights for different source types
    AUTHORITY_WEIGHTS = {
        "EARNINGS_CALL": 0.9,
        "DART_FILING": 0.95,
        "IR_MATERIAL": 0.85,
        "SECURITIES_REPORT": 0.7
    }
    
    def __init__(self, llm_router: Optional[LLMRouter] = None):
        """
        Initialize Assumption Extractor
        
        Args:
            llm_router: LLM Router instance (creates default if not provided)
        """
        self.llm_router = llm_router or get_llm_router()
    
    def extract_assumptions(
        self,
        content: str,
        ticker: str,
        company_name: Optional[str] = None,
        source_type: str = "EARNINGS_CALL",
        source_id: Optional[str] = None
    ) -> AssumptionExtractionResult:
        """
        Extract assumptions from content
        
        Args:
            content: Report/filing content text
            ticker: Stock ticker symbol
            company_name: Company name
            source_type: Type of source (EARNINGS_CALL, DART_FILING, etc.)
            source_id: ID of the source document
            
        Returns:
            AssumptionExtractionResult with extracted assumptions
        """
        try:
            # Truncate content if too long
            max_content_length = 8000
            if len(content) > max_content_length:
                content = content[:max_content_length]
                logger.warning(f"Content truncated to {max_content_length} characters")
            
            # Generate extraction prompt
            prompt = self._build_extraction_prompt(content, company_name)
            
            # Generate system prompt
            system_prompt = self._build_system_prompt()
            
            # Get structured response from LLM
            response = self.llm_router.generate_structured(
                prompt=prompt,
                system_prompt=system_prompt,
                schema=self._get_extraction_schema()
            )
            
            # Parse response
            assumptions_data = response.get("assumptions", [])
            
            # Convert to ExtractedAssumption objects
            extracted_assumptions = []
            for assumption_data in assumptions_data:
                try:
                    # Apply authority weight to confidence
                    base_confidence = assumption_data.get("confidence", 0.5)
                    authority_weight = self.AUTHORITY_WEIGHTS.get(source_type, 0.7)
                    adjusted_confidence = min(1.0, base_confidence * authority_weight)
                    
                    assumption = ExtractedAssumption(
                        assumption_text=assumption_data.get("assumption_text", ""),
                        assumption_category=assumption_data.get("assumption_category", "REVENUE"),
                        time_horizon=assumption_data.get("time_horizon", "MEDIUM"),
                        predicted_value=assumption_data.get("predicted_value"),
                        metric_name=assumption_data.get("metric_name"),
                        verification_date=assumption_data.get("verification_date"),
                        confidence=adjusted_confidence,
                        reasoning=assumption_data.get("reasoning")
                    )
                    extracted_assumptions.append(assumption)
                except Exception as e:
                    logger.error(f"Error parsing assumption: {e}")
                    continue
            
            logger.info(f"Extracted {len(extracted_assumptions)} assumptions from {source_type}")
            
            return AssumptionExtractionResult(
                assumptions=extracted_assumptions,
                ticker=ticker,
                company_name=company_name,
                source_type=source_type,
                source_id=source_id
            )
            
        except Exception as e:
            logger.error(f"Error extracting assumptions: {e}")
            return AssumptionExtractionResult(
                assumptions=[],
                ticker=ticker,
                company_name=company_name,
                source_type=source_type,
                source_id=source_id
            )
    
    def _build_extraction_prompt(self, content: str, company_name: Optional[str] = None) -> str:
        """Build the extraction prompt for LLM"""
        company_context = f"for {company_name}" if company_name else ""
        
        return f"""Extract investment assumptions from the following report {company_context}.

Focus on identifying explicit or implicit assumptions about:
1. REVENUE: Sales, revenue, or business growth projections
2. MARGIN: Profitability, margin improvements, cost structures
3. MACRO: Macro economic factors (interest rates, exchange rates, etc.)
4. CAPACITY: Production capacity, supply chain capabilities
5. MARKET_SHARE: Market position, competitive advantages

For each assumption, provide:
- The exact assumption text
- Category (REVENUE, MARGIN, MACRO, CAPACITY, MARKET_SHARE)
- Time horizon (SHORT: <3 months, MEDIUM: 3-12 months, LONG: >12 months)
- Predicted value if mentioned (e.g., "1조", "20%")
- Metric name (e.g., "HBM 매출", "GP 마진")
- Verification date if mentioned (YYYY-MM-DD format)
- Confidence score (0.0-1.0) based on how explicit and certain the assumption is
- Brief reasoning for the assumption

Content:
{content}

Return JSON with this structure:
{{
    "assumptions": [
        {{
            "assumption_text": "Q3 HBM 매출 1조 달성 예상",
            "assumption_category": "REVENUE",
            "time_horizon": "SHORT",
            "predicted_value": "1조",
            "metric_name": "HBM 매출",
            "verification_date": "2024-10-31",
            "confidence": 0.8,
            "reasoning": "Company explicitly stated target in earnings call"
        }}
    ]
}}"""
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for LLM"""
        return """You are an expert financial analyst specializing in extracting investment assumptions from corporate reports and filings.

Your task is to identify and extract explicit or implicit assumptions about future business performance.

Key principles:
1. Focus on forward-looking statements and projections
2. Distinguish between facts and assumptions
3. Extract the most important and actionable assumptions
4. Assign confidence based on the explicitness and certainty of the statement
5. Use Korean language for assumption texts when the content is in Korean

Assumption categories:
- REVENUE: Sales/revenue projections, business growth targets
- MARGIN: Profitability, margin improvements, cost structure changes
- MACRO: Economic factors affecting the business (interest rates, FX, etc.)
- CAPACITY: Production capacity, supply chain, manufacturing capabilities
- MARKET_SHARE: Market position, competitive dynamics, share targets

Time horizons:
- SHORT: Less than 3 months (quarterly targets)
- MEDIUM: 3-12 months (annual targets)
- LONG: More than 12 months (strategic goals)"""
    
    def _get_extraction_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for extraction"""
        return {
            "assumptions": [
                {
                    "assumption_text": "string - the exact assumption text",
                    "assumption_category": "string - one of: REVENUE, MARGIN, MACRO, CAPACITY, MARKET_SHARE",
                    "time_horizon": "string - one of: SHORT, MEDIUM, LONG",
                    "predicted_value": "string or null - predicted value (e.g., '1조', '20%')",
                    "metric_name": "string or null - metric name (e.g., 'HBM 매출', 'GP 마진')",
                    "verification_date": "string or null - date in YYYY-MM-DD format",
                    "confidence": "number - confidence score between 0.0 and 1.0",
                    "reasoning": "string or null - brief reasoning for the assumption"
                }
            ]
        }
    
    def to_investment_assumption(
        self,
        extracted: ExtractedAssumption,
        ticker: str,
        company_name: Optional[str] = None,
        source_type: str = "EARNINGS_CALL",
        source_id: Optional[str] = None
    ) -> InvestmentAssumption:
        """
        Convert ExtractedAssumption to InvestmentAssumption model
        
        Args:
            extracted: Extracted assumption
            ticker: Stock ticker
            company_name: Company name
            source_type: Source type
            source_id: Source ID
            
        Returns:
            InvestmentAssumption model instance
        """
        # Parse verification date
        verification_date = None
        if extracted.verification_date:
            try:
                verification_date = datetime.strptime(extracted.verification_date, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Invalid verification date format: {extracted.verification_date}")
        
        # Estimate verification date if not provided
        if verification_date is None:
            verification_date = self._estimate_verification_date(extracted.time_horizon)
        
        return InvestmentAssumption(
            ticker=ticker,
            company_name=company_name,
            assumption_text=extracted.assumption_text,
            assumption_category=extracted.assumption_category,
            time_horizon=extracted.time_horizon,
            predicted_value=extracted.predicted_value,
            metric_name=extracted.metric_name,
            verification_date=verification_date,
            model_confidence_at_generation=extracted.confidence,
            source_type=source_type,
            source_id=source_id,
            status="PENDING"
        )
    
    def _estimate_verification_date(self, time_horizon: str) -> date:
        """
        Estimate verification date based on time horizon
        
        Args:
            time_horizon: SHORT, MEDIUM, or LONG
            
        Returns:
            Estimated verification date
        """
        today = date.today()
        
        if time_horizon == "SHORT":
            # 3 months from now
            return today + timedelta(days=90)
        elif time_horizon == "MEDIUM":
            # 6 months from now
            return today + timedelta(days=180)
        else:  # LONG
            # 12 months from now
            return today + timedelta(days=365)


# ──── Convenience Functions ────
def extract_assumptions_from_content(
    content: str,
    ticker: str,
    company_name: Optional[str] = None,
    source_type: str = "EARNINGS_CALL",
    source_id: Optional[str] = None
) -> AssumptionExtractionResult:
    """
    Convenience function to extract assumptions from content
    
    Args:
        content: Report/filing content
        ticker: Stock ticker
        company_name: Company name
        source_type: Source type
        source_id: Source ID
        
    Returns:
        AssumptionExtractionResult
    """
    extractor = AssumptionExtractor()
    return extractor.extract_assumptions(
        content=content,
        ticker=ticker,
        company_name=company_name,
        source_type=source_type,
        source_id=source_id
    )


def convert_to_assumption_models(
    result: AssumptionExtractionResult
) -> List[InvestmentAssumption]:
    """
    Convert extraction result to InvestmentAssumption models
    
    Args:
        result: AssumptionExtractionResult
        
    Returns:
        List of InvestmentAssumption models
    """
    extractor = AssumptionExtractor()
    return [
        extractor.to_investment_assumption(
            extracted=assumption,
            ticker=result.ticker,
            company_name=result.company_name,
            source_type=result.source_type,
            source_id=result.source_id
        )
        for assumption in result.assumptions
    ]
