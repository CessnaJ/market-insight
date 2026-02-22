"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, Clock, BarChart3, RefreshCw, AlertCircle } from "lucide-react";

// Types
interface PriceAttribution {
  id: string;
  ticker: string;
  company_name: string | null;
  event_date: string;
  price_change_pct: number;
  dominant_timeframe: string | null;
  confidence_score: number | null;
  temporal_breakdown: string | null;
  ai_analysis_summary: string | null;
}

interface TemporalBreakdown {
  short_term?: string;
  medium_term?: string;
  long_term?: string;
}

export default function TemporalAnalysisPage() {
  const [attributions, setAttributions] = useState<PriceAttribution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAttribution, setSelectedAttribution] = useState<PriceAttribution | null>(null);

  const API_BASE = "http://localhost:8000/api/v1";

  const fetchAttributions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_BASE}/temporal-analysis/attributions`);
      if (!response.ok) throw new Error("Failed to fetch temporal attributions");
      const data = await response.json();
      setAttributions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAttributions();
  }, []);

  const parseBreakdown = (breakdownStr: string | null): TemporalBreakdown | null => {
    if (!breakdownStr) return null;
    try {
      return JSON.parse(breakdownStr);
    } catch {
      return null;
    }
  };

  const getTimeframeColor = (timeframe: string | null) => {
    switch (timeframe) {
      case "short":
        return "bg-blue-100 text-blue-700";
      case "medium":
        return "bg-purple-100 text-purple-700";
      case "long":
        return "bg-green-100 text-green-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  const getTimeframeLabel = (timeframe: string | null) => {
    switch (timeframe) {
      case "short":
        return "단기 (1주일 이내)";
      case "medium":
        return "중기 (1주일~3개월)";
      case "long":
        return "장기 (3개월 이상)";
      default:
        return "알 수 없음";
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-red-600">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="h-8 w-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">시계열 가격 분석</h1>
                <p className="text-sm text-gray-600">가격 변동의 시간대별 원인 분석</p>
              </div>
            </div>
            <button
              onClick={fetchAttributions}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">총 분석 건수</p>
                <p className="text-2xl font-bold text-gray-900">{attributions.length}</p>
              </div>
              <BarChart3 className="h-8 w-8 text-blue-600" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">단기 요인 우세</p>
                <p className="text-2xl font-bold text-blue-600">
                  {attributions.filter(a => a.dominant_timeframe === "short").length}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-blue-600" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">중기 요인 우세</p>
                <p className="text-2xl font-bold text-purple-600">
                  {attributions.filter(a => a.dominant_timeframe === "medium").length}
                </p>
              </div>
              <Clock className="h-8 w-8 text-purple-600" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">장기 요인 우세</p>
                <p className="text-2xl font-bold text-green-600">
                  {attributions.filter(a => a.dominant_timeframe === "long").length}
                </p>
              </div>
              <TrendingDown className="h-8 w-8 text-green-600" />
            </div>
          </div>
        </div>

        {/* Attributions List */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">가격 변동 분석 기록</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {attributions.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                분석 데이터가 없습니다
              </div>
            ) : (
              attributions.map((attribution) => {
                const breakdown = parseBreakdown(attribution.temporal_breakdown);
                return (
                  <div
                    key={attribution.id}
                    className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition"
                    onClick={() => setSelectedAttribution(attribution)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">
                            {attribution.company_name || attribution.ticker}
                          </h3>
                          <span className="text-sm text-gray-600">({attribution.ticker})</span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTimeframeColor(attribution.dominant_timeframe)}`}>
                            {getTimeframeLabel(attribution.dominant_timeframe)}
                          </span>
                        </div>
                        <div className="flex items-center gap-6 text-sm text-gray-600 mb-2">
                          <span>날짜: {attribution.event_date}</span>
                          <span className={`font-semibold ${attribution.price_change_pct >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
                            {attribution.price_change_pct >= 0 ? '+' : ''}{attribution.price_change_pct.toFixed(2)}%
                          </span>
                          <span>신뢰도: {((attribution.confidence_score || 0) * 100).toFixed(0)}%</span>
                        </div>
                        {breakdown && (
                          <div className="grid grid-cols-3 gap-4 mt-3">
                            {breakdown.short_term && (
                              <div className="bg-blue-50 p-3 rounded">
                                <p className="text-xs font-medium text-blue-700 mb-1">단기 요인</p>
                                <p className="text-sm text-gray-700">{breakdown.short_term}</p>
                              </div>
                            )}
                            {breakdown.medium_term && (
                              <div className="bg-purple-50 p-3 rounded">
                                <p className="text-xs font-medium text-purple-700 mb-1">중기 요인</p>
                                <p className="text-sm text-gray-700">{breakdown.medium_term}</p>
                              </div>
                            )}
                            {breakdown.long_term && (
                              <div className="bg-green-50 p-3 rounded">
                                <p className="text-xs font-medium text-green-700 mb-1">장기 요인</p>
                                <p className="text-sm text-gray-700">{breakdown.long_term}</p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      <AlertCircle className="h-5 w-5 text-gray-400" />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </main>

      {/* Detail Modal */}
      {selectedAttribution && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                {selectedAttribution.company_name || selectedAttribution.ticker}
              </h3>
              <button
                onClick={() => setSelectedAttribution(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            <div className="px-6 py-4">
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600 mb-1">이벤트 날짜</p>
                  <p className="text-gray-900">{selectedAttribution.event_date}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">가격 변동</p>
                  <p className={`text-lg font-semibold ${selectedAttribution.price_change_pct >= 0 ? 'text-red-600' : 'text-blue-600'}`}>
                    {selectedAttribution.price_change_pct >= 0 ? '+' : ''}{selectedAttribution.price_change_pct.toFixed(2)}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">주요 시간대</p>
                  <span className={`px-2 py-1 rounded-full text-sm font-medium ${getTimeframeColor(selectedAttribution.dominant_timeframe)}`}>
                    {getTimeframeLabel(selectedAttribution.dominant_timeframe)}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">신뢰도</p>
                  <p className="text-gray-900">{((selectedAttribution.confidence_score || 0) * 100).toFixed(0)}%</p>
                </div>
                {selectedAttribution.ai_analysis_summary && (
                  <div>
                    <p className="text-sm text-gray-600 mb-1">AI 분석 요약</p>
                    <p className="text-gray-900 whitespace-pre-wrap">{selectedAttribution.ai_analysis_summary}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
