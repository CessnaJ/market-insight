"use client";

import { useState, useEffect } from "react";
import { CheckCircle, XCircle, Clock, AlertTriangle, RefreshCw, Filter } from "lucide-react";

// Types
interface InvestmentAssumption {
  id: string;
  ticker: string;
  company_name: string | null;
  assumption_text: string;
  assumption_category: string;
  time_horizon: string;
  predicted_value: string | null;
  metric_name: string | null;
  verification_date: string | null;
  actual_value: string | null;
  is_correct: boolean | null;
  validation_source: string | null;
  model_confidence_at_generation: number;
  status: string;
  source_type: string | null;
  source_id: string | null;
  created_at: string;
  updated_at: string;
}

export default function AssumptionsPage() {
  const [assumptions, setAssumptions] = useState<InvestmentAssumption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [selectedAssumption, setSelectedAssumption] = useState<InvestmentAssumption | null>(null);

  const API_BASE = "http://localhost:8000/api/v1";

  const fetchAssumptions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_BASE}/assumptions/`);
      if (!response.ok) throw new Error("Failed to fetch assumptions");
      const data = await response.json();
      setAssumptions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssumptions();
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "VERIFIED":
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case "FAILED":
        return <XCircle className="h-5 w-5 text-red-600" />;
      case "PENDING":
        return <Clock className="h-5 w-5 text-yellow-600" />;
      default:
        return <AlertTriangle className="h-5 w-5 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "VERIFIED":
        return "bg-green-100 text-green-700";
      case "FAILED":
        return "bg-red-100 text-red-700";
      case "PENDING":
        return "bg-yellow-100 text-yellow-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "VERIFIED":
        return "검증 완료 (정답)";
      case "FAILED":
        return "검증 완료 (오답)";
      case "PENDING":
        return "검증 대기";
      default:
        return status;
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case "REVENUE":
        return "매출";
      case "MARGIN":
        return "마진";
      case "MACRO":
        return "매크로";
      case "CAPACITY":
        return "생산 능력";
      case "MARKET_SHARE":
        return "시장 점유율";
      default:
        return category;
    }
  };

  const getTimeHorizonLabel = (horizon: string) => {
    switch (horizon) {
      case "SHORT":
        return "단기";
      case "MEDIUM":
        return "중기";
      case "LONG":
        return "장기";
      default:
        return horizon;
    }
  };

  const filteredAssumptions = assumptions.filter(a => {
    if (filter !== "all" && a.status !== filter) return false;
    if (categoryFilter !== "all" && a.assumption_category !== categoryFilter) return false;
    return true;
  });

  const pendingCount = assumptions.filter(a => a.status === "PENDING").length;
  const verifiedCount = assumptions.filter(a => a.status === "VERIFIED").length;
  const failedCount = assumptions.filter(a => a.status === "FAILED").length;
  const accuracyRate = verifiedCount + failedCount > 0
    ? ((verifiedCount / (verifiedCount + failedCount)) * 100).toFixed(1)
    : "N/A";

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
              <CheckCircle className="h-8 w-8 text-green-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">투자 가정 추적</h1>
                <p className="text-sm text-gray-600">투자 가정의 정확도를 추적하고 검증합니다</p>
              </div>
            </div>
            <button
              onClick={fetchAssumptions}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
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
                <p className="text-sm text-gray-600">총 가정 수</p>
                <p className="text-2xl font-bold text-gray-900">{assumptions.length}</p>
              </div>
              <Filter className="h-8 w-8 text-gray-600" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">검증 대기</p>
                <p className="text-2xl font-bold text-yellow-600">{pendingCount}</p>
              </div>
              <Clock className="h-8 w-8 text-yellow-600" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">정확도</p>
                <p className="text-2xl font-bold text-green-600">{accuracyRate}%</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">검증 완료</p>
                <p className="text-2xl font-bold text-blue-600">
                  {verifiedCount + failedCount}
                </p>
              </div>
              <AlertTriangle className="h-8 w-8 text-blue-600" />
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">상태:</span>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">전체</option>
                <option value="PENDING">검증 대기</option>
                <option value="VERIFIED">정답</option>
                <option value="FAILED">오답</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">카테고리:</span>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">전체</option>
                <option value="REVENUE">매출</option>
                <option value="MARGIN">마진</option>
                <option value="MACRO">매크로</option>
                <option value="CAPACITY">생산 능력</option>
                <option value="MARKET_SHARE">시장 점유율</option>
              </select>
            </div>
          </div>
        </div>

        {/* Assumptions List */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              투자 가정 목록 ({filteredAssumptions.length}건)
            </h2>
          </div>
          <div className="divide-y divide-gray-200">
            {filteredAssumptions.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                표시할 가정이 없습니다
              </div>
            ) : (
              filteredAssumptions.map((assumption) => (
                <div
                  key={assumption.id}
                  className="px-6 py-4 hover:bg-gray-50 cursor-pointer transition"
                  onClick={() => setSelectedAssumption(assumption)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">
                          {assumption.company_name || assumption.ticker}
                        </h3>
                        <span className="text-sm text-gray-600">({assumption.ticker})</span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(assumption.status)}`}>
                          {getStatusLabel(assumption.status)}
                        </span>
                      </div>
                      <p className="text-gray-700 mb-3">{assumption.assumption_text}</p>
                      <div className="flex items-center gap-6 text-sm text-gray-600">
                        <span>카테고리: {getCategoryLabel(assumption.assumption_category)}</span>
                        <span>시간대: {getTimeHorizonLabel(assumption.time_horizon)}</span>
                        {assumption.predicted_value && (
                          <span>예상값: {assumption.predicted_value}</span>
                        )}
                        {assumption.actual_value && (
                          <span className={`font-semibold ${assumption.is_correct ? 'text-green-600' : 'text-red-600'}`}>
                            실제값: {assumption.actual_value}
                          </span>
                        )}
                        <span>신뢰도: {(assumption.model_confidence_at_generation * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <div className="ml-4">
                      {getStatusIcon(assumption.status)}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>

      {/* Detail Modal */}
      {selectedAssumption && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                투자 가정 상세
              </h3>
              <button
                onClick={() => setSelectedAssumption(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            <div className="px-6 py-4">
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600 mb-1">종목</p>
                  <p className="text-gray-900">
                    {selectedAssumption.company_name || selectedAssumption.ticker} ({selectedAssumption.ticker})
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">가정 내용</p>
                  <p className="text-gray-900">{selectedAssumption.assumption_text}</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">카테고리</p>
                    <p className="text-gray-900">{getCategoryLabel(selectedAssumption.assumption_category)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">시간대</p>
                    <p className="text-gray-900">{getTimeHorizonLabel(selectedAssumption.time_horizon)}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">예상값</p>
                    <p className="text-gray-900">{selectedAssumption.predicted_value || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">실제값</p>
                    <p className={`text-gray-900 font-semibold ${selectedAssumption.is_correct ? 'text-green-600' : selectedAssumption.is_correct === false ? 'text-red-600' : ''}`}>
                      {selectedAssumption.actual_value || 'N/A'}
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">상태</p>
                  <span className={`px-2 py-1 rounded-full text-sm font-medium ${getStatusColor(selectedAssumption.status)}`}>
                    {getStatusLabel(selectedAssumption.status)}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">모델 신뢰도</p>
                  <p className="text-gray-900">{(selectedAssumption.model_confidence_at_generation * 100).toFixed(0)}%</p>
                </div>
                {selectedAssumption.verification_date && (
                  <div>
                    <p className="text-sm text-gray-600 mb-1">검증일</p>
                    <p className="text-gray-900">{selectedAssumption.verification_date}</p>
                  </div>
                )}
                {selectedAssumption.source_type && (
                  <div>
                    <p className="text-sm text-gray-600 mb-1">출처 유형</p>
                    <p className="text-gray-900">{selectedAssumption.source_type}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm text-gray-600 mb-1">생성일</p>
                  <p className="text-gray-900">{new Date(selectedAssumption.created_at).toLocaleString('ko-KR')}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
