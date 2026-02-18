"use client";

import { useState, useEffect } from "react";
import { FileText, Calendar, RefreshCw } from "lucide-react";

interface DailyReport {
  id: string;
  date: string;
  report_markdown: string;
  portfolio_section: string;
  content_section: string;
  thought_section: string;
  ai_opinion: string;
  action_items?: string;
  created_at: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState<DailyReport | null>(null);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/reports/");
      if (response.ok) {
        const data = await response.json();
        setReports(data);
      }
    } catch (error) {
      console.error("Error fetching reports:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDailyReport = async () => {
    try {
      const response = await fetch("http://localhost:3000/api/reports/generate/daily", {
        method: "POST",
      });

      if (response.ok) {
        fetchReports();
      }
    } catch (error) {
      console.error("Error generating report:", error);
    }
  };

  const handleGenerateWeeklyReport = async () => {
    try {
      const response = await fetch("http://localhost:3000/api/reports/generate/weekly", {
        method: "POST",
      });

      if (response.ok) {
        fetchReports();
      }
    } catch (error) {
      console.error("Error generating weekly report:", error);
    }
  };

  const formatMarkdown = (markdown: string) => {
    // Simple markdown formatting
    return markdown
      .replace(/^### (.*$)/gm, '<h3 class="text-xl font-bold mt-4 mb-2">$1</h3>')
      .replace(/^## (.*$)/gm, '<h2 class="text-2xl font-bold mt-6 mb-3">$1</h2>')
      .replace(/^# (.*$)/gm, '<h1 class="text-3xl font-bold mt-8 mb-4">$1</h1>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br />');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">로딩 중...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <FileText className="w-8 h-8" />
          리포트
        </h1>
        <div className="flex gap-2">
          <button
            onClick={handleGenerateDailyReport}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700 transition"
          >
            <Calendar className="w-5 h-5" />
            일일 리포트 생성
          </button>
          <button
            onClick={handleGenerateWeeklyReport}
            className="bg-purple-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-purple-700 transition"
          >
            <Calendar className="w-5 h-5" />
            주간 리포트 생성
          </button>
          <button
            onClick={fetchReports}
            className="bg-gray-800 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-gray-900 transition"
          >
            <RefreshCw className="w-5 h-5" />
            새로고침
          </button>
        </div>
      </div>

      {/* Reports List */}
      <div className="space-y-4">
        {reports.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            리포트가 아직 없습니다.
          </div>
        ) : (
          reports.map((report) => (
            <div
              key={report.id}
              className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm hover:shadow-md transition cursor-pointer"
              onClick={() => setSelectedReport(report)}
            >
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xl font-bold">
                  {new Date(report.date).toLocaleDateString("ko-KR", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </h2>
                <span className="text-gray-500 text-sm">
                  {new Date(report.created_at).toLocaleString("ko-KR")}
                </span>
              </div>
              <div
                className="text-gray-700 line-clamp-3"
                dangerouslySetInnerHTML={{
                  __html: formatMarkdown(report.report_markdown),
                }}
              />
            </div>
          ))
        )}
      </div>

      {/* Report Detail Modal */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white rounded-lg p-6 w-full max-w-4xl my-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold">
                {new Date(selectedReport.date).toLocaleDateString("ko-KR", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}{" "}
                리포트
              </h2>
              <button
                onClick={() => setSelectedReport(null)}
                className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <div
              className="prose max-w-none overflow-y-auto max-h-[70vh] text-gray-800"
              dangerouslySetInnerHTML={{
                __html: formatMarkdown(selectedReport.report_markdown),
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
