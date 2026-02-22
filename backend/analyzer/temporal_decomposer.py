"""Temporal Signal Decomposition for Price Attribution Analysis

Decomposes price changes into short-term, medium-term, and long-term factors
using AI-powered analysis with Claude 3.7.
"""

import logging
import json
from datetime import date
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from sqlmodel import Session

from analyzer.llm_router import LLMRouter, LLMProvider
from analyzer.context_gatherer import ContextGatherer
from storage.db import get_session, add_price_attribution, get_price_attribution_by_date
from storage.models import PriceAttribution
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Temporal Decomposer Settings"""
    # LLM settings
    llm_provider: str = "anthropic"  # Use Claude 3.7 for temporal analysis
    llm_model: str = "claude-3-7-sonnet-20250219"  # Claude 3.7 model
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()


@dataclass
class TemporalBreakdown:
    """Temporal breakdown of price change factors"""
    short_term: Dict[str, Any]  # 1 week or less
    medium_term: Dict[str, Any]  # 1 week to 3 months
    long_term: Dict[str, Any]  # 3 months or more
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class TemporalAnalysisResult:
    """Complete temporal analysis result"""
    ticker: str
    company_name: Optional[str]
    event_date: date
    price_change_pct: float
    short_term_analysis: Dict[str, Any]
    medium_term_analysis: Dict[str, Any]
    long_term_analysis: Dict[str, Any]
    comprehensive_analysis: Dict[str, Any]
    confidence_score: float
    dominant_timeframe: str
    ai_analysis_summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class TemporalSignalDecomposer:
    """
    Decomposes price signals into temporal factors using AI analysis
    
    Usage:
        decomposer = TemporalSignalDecomposer()
        result = decomposer.decompose_price_signal(
            ticker="005930",
            company_name="삼성전자",
            event_date=date(2024, 1, 15),
            price_change_pct=3.5
        )
    """

    def __init__(
        self,
        llm_router: Optional[LLMRouter] = None,
        session: Optional[Session] = None
    ):
        """
        Initialize Temporal Signal Decomposer
        
        Args:
            llm_router: LLM router instance (creates new if not provided)
            session: Database session (creates new if not provided)
        """
        self.llm_router = llm_router or LLMRouter(
            provider=LLMProvider.ANTHROPIC,
            model=settings.llm_model
        )
        self.session = session
        self._session_created = False
        
        if self.session is None:
            self.session = next(get_session())
            self._session_created = True
        
        # Load prompts
        self.prompts = self._load_prompts()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session if created"""
        if self._session_created and self.session:
            self.session.close()

    def _load_prompts(self) -> Dict[str, str]:
        """
        Load prompt templates from YAML file
        
        Returns:
            Dictionary of prompts
        """
        try:
            import yaml
            with open("config/prompts.yaml", "r", encoding="utf-8") as f:
                prompts = yaml.safe_load(f)
                return prompts.get("temporal", {})
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
            return {}

    def decompose_price_signal(
        self,
        ticker: str,
        event_date: date,
        price_change_pct: float,
        company_name: Optional[str] = None,
        save_to_db: bool = True
    ) -> TemporalAnalysisResult:
        """
        Decompose price signal into temporal factors
        
        Args:
            ticker: Stock ticker symbol
            event_date: Date of price event
            price_change_pct: Price change percentage
            company_name: Optional company name
            save_to_db: Whether to save result to database
            
        Returns:
            TemporalAnalysisResult with complete analysis
        """
        logger.info(
            f"Decomposing price signal for {ticker} on {event_date} "
            f"(change: {price_change_pct}%)"
        )
        
        # Step 1: Gather context
        context = self._gather_context(ticker, event_date, company_name)
        
        # Step 2: Analyze short-term factors
        short_term = self._analyze_short_term(context)
        
        # Step 3: Analyze medium-term factors
        medium_term = self._analyze_medium_term(context)
        
        # Step 4: Analyze long-term factors
        long_term = self._analyze_long_term(context)
        
        # Step 5: Comprehensive analysis
        comprehensive = self._analyze_comprehensive(
            context, short_term, medium_term, long_term
        )
        
        # Step 6: Build result
        result = TemporalAnalysisResult(
            ticker=ticker,
            company_name=company_name,
            event_date=event_date,
            price_change_pct=price_change_pct,
            short_term_analysis=short_term,
            medium_term_analysis=medium_term,
            long_term_analysis=long_term,
            comprehensive_analysis=comprehensive,
            confidence_score=comprehensive.get("overall_confidence", 0.5),
            dominant_timeframe=comprehensive.get("dominant_timeframe", "unknown"),
            ai_analysis_summary=self._generate_summary(comprehensive)
        )
        
        # Step 7: Save to database if requested
        if save_to_db:
            self._save_result(result)
        
        return result

    def _gather_context(
        self,
        ticker: str,
        event_date: date,
        company_name: Optional[str]
    ) -> Dict[str, Any]:
        """
        Gather context data for analysis
        
        Args:
            ticker: Stock ticker
            event_date: Event date
            company_name: Company name
            
        Returns:
            Context dictionary
        """
        with ContextGatherer(session=self.session) as gatherer:
            return gatherer.gather_context(ticker, event_date, company_name)

    def _analyze_short_term(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze short-term factors (1 week or less)
        
        Args:
            context: Context dictionary
            
        Returns:
            Short-term analysis result
        """
        prompt_template = self.prompts.get("short_term_analysis", "")
        
        prompt = prompt_template.format(
            ticker=context.get("ticker", ""),
            company_name=context.get("company_name", ""),
            event_date=context.get("event_date", ""),
            price_change_pct=context.get("price_change_pct", 0),
            macro_context=context.get("macro_context", ""),
            supply_demand_data=context.get("supply_demand_data", ""),
            recent_news=context.get("recent_news", ""),
            sentiment_indicators=context.get("sentiment_indicators", "")
        )
        
        system_prompt = self.prompts.get("system", "")
        
        try:
            result = self.llm_router.generate_structured(
                prompt=prompt,
                system_prompt=system_prompt,
                provider=LLMProvider.ANTHROPIC
            )
            logger.info(f"Short-term analysis completed for {context.get('ticker')}")
            return result
        except Exception as e:
            logger.error(f"Error in short-term analysis: {e}")
            return self._get_fallback_short_term()

    def _analyze_medium_term(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze medium-term factors (1 week to 3 months)
        
        Args:
            context: Context dictionary
            
        Returns:
            Medium-term analysis result
        """
        prompt_template = self.prompts.get("medium_term_analysis", "")
        
        prompt = prompt_template.format(
            ticker=context.get("ticker", ""),
            company_name=context.get("company_name", ""),
            analysis_period=f"{context.get('event_date', '')} - 3개월",
            earnings_revision=context.get("earnings_revision", ""),
            sector_rotation=context.get("sector_rotation", ""),
            recent_earnings=context.get("recent_earnings", ""),
            analyst_opinions=context.get("analyst_opinions", "")
        )
        
        system_prompt = self.prompts.get("system", "")
        
        try:
            result = self.llm_router.generate_structured(
                prompt=prompt,
                system_prompt=system_prompt,
                provider=LLMProvider.ANTHROPIC
            )
            logger.info(f"Medium-term analysis completed for {context.get('ticker')}")
            return result
        except Exception as e:
            logger.error(f"Error in medium-term analysis: {e}")
            return self._get_fallback_medium_term()

    def _analyze_long_term(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze long-term factors (3 months or more)
        
        Args:
            context: Context dictionary
            
        Returns:
            Long-term analysis result
        """
        prompt_template = self.prompts.get("long_term_analysis", "")
        
        prompt = prompt_template.format(
            ticker=context.get("ticker", ""),
            company_name=context.get("company_name", ""),
            structural_competitiveness=context.get("structural_competitiveness", ""),
            market_share=context.get("market_share", ""),
            industry_structure=context.get("industry_structure", ""),
            innovation=context.get("innovation", "")
        )
        
        system_prompt = self.prompts.get("system", "")
        
        try:
            result = self.llm_router.generate_structured(
                prompt=prompt,
                system_prompt=system_prompt,
                provider=LLMProvider.ANTHROPIC
            )
            logger.info(f"Long-term analysis completed for {context.get('ticker')}")
            return result
        except Exception as e:
            logger.error(f"Error in long-term analysis: {e}")
            return self._get_fallback_long_term()

    def _analyze_comprehensive(
        self,
        context: Dict[str, Any],
        short_term: Dict[str, Any],
        medium_term: Dict[str, Any],
        long_term: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis combining all timeframes
        
        Args:
            context: Context dictionary
            short_term: Short-term analysis
            medium_term: Medium-term analysis
            long_term: Long-term analysis
            
        Returns:
            Comprehensive analysis result
        """
        prompt_template = self.prompts.get("comprehensive_analysis", "")
        
        prompt = prompt_template.format(
            ticker=context.get("ticker", ""),
            company_name=context.get("company_name", ""),
            event_date=context.get("event_date", ""),
            price_change_pct=context.get("price_change_pct", 0),
            short_term_result=json.dumps(short_term, ensure_ascii=False),
            medium_term_result=json.dumps(medium_term, ensure_ascii=False),
            long_term_result=json.dumps(long_term, ensure_ascii=False)
        )
        
        system_prompt = self.prompts.get("system", "")
        
        try:
            result = self.llm_router.generate_structured(
                prompt=prompt,
                system_prompt=system_prompt,
                provider=LLMProvider.ANTHROPIC
            )
            logger.info(f"Comprehensive analysis completed for {context.get('ticker')}")
            return result
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            return self._get_fallback_comprehensive()

    def _generate_summary(self, comprehensive: Dict[str, Any]) -> str:
        """
        Generate human-readable summary from comprehensive analysis
        
        Args:
            comprehensive: Comprehensive analysis result
            
        Returns:
            Summary text
        """
        summary_parts = []
        
        summary_parts.append(f"주요 시간대: {comprehensive.get('dominant_timeframe', 'unknown')}")
        summary_parts.append(f"주요 요인: {comprehensive.get('dominant_factor', 'unknown')}")
        
        attribution = comprehensive.get("attribution_breakdown", {})
        summary_parts.append(
            f"요인 분해: 단기 {attribution.get('short_term', 0):.1%}, "
            f"중기 {attribution.get('medium_term', 0):.1%}, "
            f"장기 {attribution.get('long_term', 0):.1%}"
        )
        
        insights = comprehensive.get("key_insights", [])
        if insights:
            summary_parts.append("\n주요 인사이트:")
            for insight in insights[:3]:
                summary_parts.append(f"- {insight}")
        
        return "\n".join(summary_parts)

    def _save_result(self, result: TemporalAnalysisResult) -> None:
        """
        Save analysis result to database
        
        Args:
            result: Analysis result to save
        """
        try:
            # Check if attribution already exists
            existing = get_price_attribution_by_date(
                self.session,
                result.ticker,
                result.event_date
            )
            
            if existing:
                # Update existing record
                from storage.db import update_price_attribution
                update_price_attribution(
                    self.session,
                    existing.id,
                    price_change_pct=result.price_change_pct,
                    temporal_breakdown=json.dumps({
                        "short_term": result.short_term_analysis,
                        "medium_term": result.medium_term_analysis,
                        "long_term": result.long_term_analysis,
                        "comprehensive": result.comprehensive_analysis
                    }, ensure_ascii=False),
                    ai_analysis_summary=result.ai_analysis_summary,
                    confidence_score=result.confidence_score,
                    dominant_timeframe=result.dominant_timeframe
                )
                logger.info(f"Updated existing attribution for {result.ticker} on {result.event_date}")
            else:
                # Create new record
                attribution = PriceAttribution(
                    ticker=result.ticker,
                    company_name=result.company_name,
                    event_date=result.event_date,
                    price_change_pct=result.price_change_pct,
                    temporal_breakdown=json.dumps({
                        "short_term": result.short_term_analysis,
                        "medium_term": result.medium_term_analysis,
                        "long_term": result.long_term_analysis,
                        "comprehensive": result.comprehensive_analysis
                    }, ensure_ascii=False),
                    ai_analysis_summary=result.ai_analysis_summary,
                    confidence_score=result.confidence_score,
                    dominant_timeframe=result.dominant_timeframe
                )
                add_price_attribution(self.session, attribution)
                logger.info(f"Saved new attribution for {result.ticker} on {result.event_date}")
                
        except Exception as e:
            logger.error(f"Error saving attribution to database: {e}")

    def _get_fallback_short_term(self) -> Dict[str, Any]:
        """Fallback short-term analysis when LLM fails"""
        return {
            "primary_factor": "데이터 부족으로 분석 불가",
            "secondary_factors": [],
            "supply_demand": {
                "foreigner_net": "데이터 없음",
                "institution_net": "데이터 없음",
                "retail_net": "데이터 없음",
                "short_selling": "데이터 없음"
            },
            "market_sentiment": "neutral",
            "impact_score": 0.0,
            "confidence": 0.0
        }

    def _get_fallback_medium_term(self) -> Dict[str, Any]:
        """Fallback medium-term analysis when LLM fails"""
        return {
            "primary_factor": "데이터 부족으로 분석 불가",
            "secondary_factors": [],
            "earnings_revision": {
                "trend": "stable",
                "key_drivers": []
            },
            "sector_momentum": "weak",
            "valuation": "fair",
            "impact_score": 0.0,
            "confidence": 0.0
        }

    def _get_fallback_long_term(self) -> Dict[str, Any]:
        """Fallback long-term analysis when LLM fails"""
        return {
            "primary_factor": "데이터 부족으로 분석 불가",
            "secondary_factors": [],
            "structural_advantage": {
                "type": "none",
                "sustainability": "low",
                "key_factors": []
            },
            "market_position": {
                "share_trend": "stable",
                "competitive_landscape": "데이터 없음"
            },
            "growth_potential": "medium",
            "impact_score": 0.0,
            "confidence": 0.0
        }

    def _get_fallback_comprehensive(self) -> Dict[str, Any]:
        """Fallback comprehensive analysis when LLM fails"""
        return {
            "dominant_timeframe": "unknown",
            "dominant_factor": "데이터 부족으로 분석 불가",
            "attribution_breakdown": {
                "short_term": 0.33,
                "medium_term": 0.33,
                "long_term": 0.34
            },
            "key_insights": ["충분한 데이터가 필요합니다"],
            "risk_factors": [],
            "investment_implication": "데이터 부족으로 판단 보류",
            "overall_confidence": 0.0
        }


# Convenience function
def decompose_price_signal(
    ticker: str,
    event_date: date,
    price_change_pct: float,
    company_name: Optional[str] = None,
    save_to_db: bool = True
) -> TemporalAnalysisResult:
    """
    Quick function to decompose price signal
    
    Args:
        ticker: Stock ticker
        event_date: Event date
        price_change_pct: Price change percentage
        company_name: Optional company name
        save_to_db: Whether to save to database
        
    Returns:
        TemporalAnalysisResult
    """
    with TemporalSignalDecomposer() as decomposer:
        return decomposer.decompose_price_signal(
            ticker, event_date, price_change_pct, company_name, save_to_db
        )
