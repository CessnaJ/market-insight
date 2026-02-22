"""Assumption Validator - Scheduled job to validate assumptions against actual data

This module provides scheduled validation of investment assumptions:
- Queries financial data for verification
- Updates assumption status (PENDING, VERIFIED, FAILED)
- Tracks assumption accuracy over time
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from sqlmodel import Session

from storage.db import (
    get_session,
    get_pending_assumptions,
    validate_assumption,
    get_assumption_by_id
)
from storage.models import InvestmentAssumption
from analyzer.llm_router import LLMRouter, get_llm_router

logger = logging.getLogger(__name__)


# ──── Mock Financial Data Provider ────
class FinancialDataProvider:
    """
    Provider for financial data to validate assumptions
    
    In production, this would connect to real financial data sources.
    For now, it provides mock data for testing.
    """
    
    # Mock data for testing
    MOCK_DATA = {
        "005930": {
            "name": "삼성전자",
            "revenue": {
                "2024-Q3": {
                    "HBM 매출": "1.2조",  # Actual: 1.2조
                    "전체 매출": "79조"
                },
                "2024-Q4": {
                    "전체 매출": "75조"
                }
            },
            "margin": {
                "2024-Q3": {
                    "GP 마진": "18%"  # Actual: 18%
                }
            }
        },
        "000660": {
            "name": "SK하이닉스",
            "revenue": {
                "2024-Q3": {
                    "HBM 매출": "0.8조"
                }
            }
        }
    }
    
    @staticmethod
    def get_financial_metric(
        ticker: str,
        metric_name: str,
        period: str
    ) -> Optional[str]:
        """
        Get financial metric for a ticker and period
        
        Args:
            ticker: Stock ticker
            metric_name: Metric name (e.g., "HBM 매출")
            period: Period identifier (e.g., "2024-Q3")
            
        Returns:
            Actual value or None if not found
        """
        mock_data = FinancialDataProvider.MOCK_DATA.get(ticker, {})
        
        # Try to find the metric in revenue or margin data
        for category in ["revenue", "margin"]:
            category_data = mock_data.get(category, {})
            period_data = category_data.get(period, {})
            value = period_data.get(metric_name)
            if value:
                return value
        
        return None
    
    @staticmethod
    def get_latest_period(ticker: str) -> Optional[str]:
        """
        Get the latest available period for a ticker
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Period identifier or None
        """
        mock_data = FinancialDataProvider.MOCK_DATA.get(ticker, {})
        
        # Find latest period in revenue data
        revenue_data = mock_data.get("revenue", {})
        if revenue_data:
            return list(revenue_data.keys())[-1]
        
        return None


# ──── Assumption Validator ────
class AssumptionValidator:
    """
    Validates investment assumptions against actual financial data
    
    Usage:
        validator = AssumptionValidator()
        results = validator.validate_pending_assumptions()
    """
    
    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        data_provider: Optional[FinancialDataProvider] = None
    ):
        """
        Initialize Assumption Validator
        
        Args:
            llm_router: LLM Router for semantic comparison
            data_provider: Financial data provider
        """
        self.llm_router = llm_router or get_llm_router()
        self.data_provider = data_provider or FinancialDataProvider()
    
    def validate_pending_assumptions(
        self,
        ticker: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Validate all pending assumptions
        
        Args:
            ticker: Optional ticker filter
            limit: Maximum number of assumptions to validate
            
        Returns:
            List of validation results
        """
        results = []
        
        with Session(get_session().bind) as session:
            # Get pending assumptions
            pending_assumptions = get_pending_assumptions(
                session=session,
                ticker=ticker,
                limit=limit
            )
            
            logger.info(f"Found {len(pending_assumptions)} pending assumptions to validate")
            
            for assumption in pending_assumptions:
                try:
                    result = self.validate_assumption(session, assumption)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error validating assumption {assumption.id}: {e}")
                    results.append({
                        "assumption_id": assumption.id,
                        "success": False,
                        "error": str(e)
                    })
        
        return results
    
    def validate_assumption(
        self,
        session: Session,
        assumption: InvestmentAssumption
    ) -> Dict[str, Any]:
        """
        Validate a single assumption
        
        Args:
            session: Database session
            assumption: InvestmentAssumption to validate
            
        Returns:
            Validation result dictionary
        """
        logger.info(f"Validating assumption {assumption.id}: {assumption.assumption_text}")
        
        # Try to get actual financial data
        actual_value = self._get_actual_value(assumption)
        
        if actual_value is None:
            # No actual data available yet
            logger.info(f"No actual data available for assumption {assumption.id}")
            return {
                "assumption_id": assumption.id,
                "success": False,
                "status": "NO_DATA",
                "message": "No actual data available yet"
            }
        
        # Compare predicted vs actual
        is_correct = self._compare_values(
            predicted=assumption.predicted_value,
            actual=actual_value,
            metric_name=assumption.metric_name
        )
        
        # Update assumption in database
        validated = validate_assumption(
            session=session,
            assumption_id=assumption.id,
            actual_value=actual_value,
            is_correct=is_correct,
            validation_source="FinancialDataProvider"
        )
        
        logger.info(
            f"Assumption {assumption.id} validated: "
            f"predicted={assumption.predicted_value}, actual={actual_value}, "
            f"correct={is_correct}"
        )
        
        return {
            "assumption_id": assumption.id,
            "success": True,
            "status": "VERIFIED" if is_correct else "FAILED",
            "predicted_value": assumption.predicted_value,
            "actual_value": actual_value,
            "is_correct": is_correct
        }
    
    def _get_actual_value(
        self,
        assumption: InvestmentAssumption
    ) -> Optional[str]:
        """
        Get actual value for an assumption
        
        Args:
            assumption: InvestmentAssumption
            
        Returns:
            Actual value or None
        """
        if not assumption.metric_name:
            return None
        
        # Determine period based on verification date
        if assumption.verification_date:
            period = self._date_to_period(assumption.verification_date)
        else:
            period = self._date_to_period(date.today())
        
        return self.data_provider.get_financial_metric(
            ticker=assumption.ticker,
            metric_name=assumption.metric_name,
            period=period
        )
    
    def _date_to_period(self, date_obj: date) -> str:
        """
        Convert date to period identifier (e.g., "2024-Q3")
        
        Args:
            date_obj: Date object
            
        Returns:
            Period string
        """
        year = date_obj.year
        quarter = (date_obj.month - 1) // 3 + 1
        return f"{year}-Q{quarter}"
    
    def _compare_values(
        self,
        predicted: Optional[str],
        actual: str,
        metric_name: Optional[str] = None
    ) -> bool:
        """
        Compare predicted and actual values
        
        Args:
            predicted: Predicted value string
            actual: Actual value string
            metric_name: Metric name for context
            
        Returns:
            True if values match within tolerance, False otherwise
        """
        if not predicted:
            return False
        
        # Try numeric comparison
        try:
            predicted_num = self._extract_number(predicted)
            actual_num = self._extract_number(actual)
            
            if predicted_num is not None and actual_num is not None:
                # Allow 10% tolerance
                tolerance = 0.1
                diff = abs(predicted_num - actual_num)
                relative_diff = diff / max(abs(actual_num), 1)
                
                return relative_diff <= tolerance
        except Exception:
            pass
        
        # Use LLM for semantic comparison
        return self._semantic_compare(predicted, actual, metric_name)
    
    def _extract_number(self, value: str) -> Optional[float]:
        """
        Extract numeric value from string
        
        Args:
            value: Value string (e.g., "1조", "20%", "1.2조")
            
        Returns:
            Numeric value or None
        """
        import re
        
        # Handle Korean units
        unit_multipliers = {
            "조": 1000000000000,
            "억": 100000000,
            "만": 10000,
            "천": 1000
        }
        
        # Extract number and unit
        match = re.search(r"([\d.]+)\s*([조억만천%]?)", value)
        if match:
            num = float(match.group(1))
            unit = match.group(2)
            
            if unit in unit_multipliers:
                return num * unit_multipliers[unit]
            elif unit == "%":
                return num
            else:
                return num
        
        return None
    
    def _semantic_compare(
        self,
        predicted: str,
        actual: str,
        metric_name: Optional[str] = None
    ) -> bool:
        """
        Use LLM to semantically compare predicted and actual values
        
        Args:
            predicted: Predicted value
            actual: Actual value
            metric_name: Metric name for context
            
        Returns:
            True if values match semantically
        """
        prompt = f"""Compare these two values and determine if they match:

Predicted: {predicted}
Actual: {actual}
Metric: {metric_name or "N/A"}

Consider:
- Are they referring to the same thing?
- Are they in the same ballpark (within reasonable tolerance)?
- Do they convey the same meaning?

Respond with JSON: {{"match": true/false, "reasoning": "explanation"}}"""
        
        try:
            response = self.llm_router.generate_structured(prompt=prompt)
            return response.get("match", False)
        except Exception as e:
            logger.error(f"Error in semantic comparison: {e}")
            return False


# ──── Scheduled Job Functions ────
def run_assumption_validation_job(
    ticker: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Run the assumption validation job
    
    Args:
        ticker: Optional ticker filter
        limit: Maximum assumptions to validate
        
    Returns:
        Job summary
    """
    logger.info("Starting assumption validation job")
    
    validator = AssumptionValidator()
    results = validator.validate_pending_assumptions(ticker=ticker, limit=limit)
    
    # Calculate summary
    total = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    verified = sum(1 for r in results if r.get("status") == "VERIFIED")
    failed = sum(1 for r in results if r.get("status") == "FAILED")
    no_data = sum(1 for r in results if r.get("status") == "NO_DATA")
    
    summary = {
        "total_assumptions_checked": total,
        "successful_validations": successful,
        "verified": verified,
        "failed": failed,
        "no_data": no_data,
        "results": results
    }
    
    logger.info(f"Assumption validation job completed: {summary}")
    
    return summary


def validate_single_assumption(assumption_id: str) -> Dict[str, Any]:
    """
    Validate a single assumption by ID
    
    Args:
        assumption_id: Assumption ID
        
    Returns:
        Validation result
    """
    with Session(get_session().bind) as session:
        assumption = get_assumption_by_id(session, assumption_id)
        
        if not assumption:
            return {
                "success": False,
                "error": f"Assumption {assumption_id} not found"
            }
        
        validator = AssumptionValidator()
        result = validator.validate_assumption(session, assumption)
        
        return result


# ──── Accuracy Tracking ────
def get_accuracy_trends(
    ticker: Optional[str] = None,
    days: int = 90
) -> Dict[str, Any]:
    """
    Get accuracy trends over time
    
    Args:
        ticker: Optional ticker filter
        days: Number of days to look back
        
    Returns:
        Accuracy trends data
    """
    from storage.db import get_assumption_accuracy_stats
    
    with Session(get_session().bind) as session:
        stats = get_assumption_accuracy_stats(
            session=session,
            ticker=ticker
        )
        
        # Get recent assumptions for trend analysis
        from sqlmodel import select
        from datetime import timedelta
        
        cutoff_date = date.today() - timedelta(days=days)
        
        query = select(InvestmentAssumption).where(
            InvestmentAssumption.status.in_(["VERIFIED", "FAILED"]),
            InvestmentAssumption.updated_at >= cutoff_date
        )
        
        if ticker:
            query = query.where(InvestmentAssumption.ticker == ticker)
        
        recent_assumptions = session.exec(query).all()
        
        # Group by week
        weekly_data = {}
        for assumption in recent_assumptions:
            week_start = assumption.updated_at - timedelta(
                days=assumption.updated_at.weekday()
            )
            week_key = week_start.strftime("%Y-%m-%d")
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {"correct": 0, "total": 0}
            
            weekly_data[week_key]["total"] += 1
            if assumption.is_correct:
                weekly_data[week_key]["correct"] += 1
        
        # Calculate weekly accuracy
        weekly_trends = []
        for week, data in sorted(weekly_data.items()):
            accuracy = data["correct"] / data["total"] if data["total"] > 0 else 0
            weekly_trends.append({
                "week": week,
                "total": data["total"],
                "correct": data["correct"],
                "accuracy": accuracy
            })
        
        return {
            "overall_stats": stats,
            "weekly_trends": weekly_trends
        }
