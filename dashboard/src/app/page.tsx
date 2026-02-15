"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, DollarSign, FileText, RefreshCw, Brain, Layout, Wifi, WifiOff } from "lucide-react";
import Link from "next/link";
import { useWebSocket } from "@/hooks/useWebSocket";

// Types
interface PortfolioHolding {
  ticker: string;
  name: string;
  shares: number;
  avg_price: number;
  current_price: number;
  current_value: number;
  pnl: number;
  pnl_pct: number;
  market: string;
}

interface PortfolioSummary {
  total_value: number;
  total_invested: number;
  total_pnl: number;
  total_pnl_pct: number;
  holdings: PortfolioHolding[];
}

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = "http://localhost:3000/api/v1";
  const WS_URL = "ws://localhost:3000/api/v1/ws";

  // WebSocket connection
  const { isConnected, lastMessage, connectionStatus } = useWebSocket(WS_URL);

  const fetchPortfolio = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_BASE}/portfolio/summary`);
      if (!response.ok) throw new Error("Failed to fetch portfolio");
      const data = await response.json();
      setPortfolio(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      switch (lastMessage.type) {
        case "portfolio_update":
          setPortfolio(lastMessage.data);
          break;
        case "price_update":
          // Update specific stock price in portfolio
          if (portfolio && lastMessage.ticker) {
            setPortfolio({
              ...portfolio,
              holdings: portfolio.holdings.map(holding =>
                holding.ticker === lastMessage.ticker
                  ? { ...holding, current_price: lastMessage.data.price }
                  : holding
              ),
            });
          }
          break;
        default:
          break;
      }
    }
  }, [lastMessage, portfolio]);

  useEffect(() => {
    fetchPortfolio();
  }, []);

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
            <div className="flex items-center gap-8">
              <h1 className="text-2xl font-bold text-gray-900">Market Insight</h1>
              <nav className="flex items-center gap-4">
                <Link
                  href="/"
                  className="text-gray-600 hover:text-gray-900 flex items-center gap-1 text-sm font-medium"
                >
                  <Layout size={16} />
                  대시보드
                </Link>
                <Link
                  href="/thoughts"
                  className="text-gray-600 hover:text-gray-900 flex items-center gap-1 text-sm font-medium"
                >
                  <Brain size={16} />
                  생각
                </Link>
                <Link
                  href="/reports"
                  className="text-gray-600 hover:text-gray-900 flex items-center gap-1 text-sm font-medium"
                >
                  <FileText size={16} />
                  리포트
                </Link>
              </nav>
            </div>
            <div className="flex items-center gap-3">
              {/* Connection Status */}
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                connectionStatus === "connected" ? "bg-green-100 text-green-700" :
                connectionStatus === "connecting" ? "bg-yellow-100 text-yellow-700" :
                connectionStatus === "error" ? "bg-red-100 text-red-700" :
                "bg-gray-100 text-gray-700"
              }`}>
                {connectionStatus === "connected" ? <Wifi size={16} /> : <WifiOff size={16} />}
                <span className="text-xs font-medium capitalize">{connectionStatus}</span>
              </div>
              <button
                onClick={fetchPortfolio}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                <RefreshCw size={16} />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center gap-3 mb-2">
              <DollarSign className="text-blue-600" size={24} />
              <h3 className="text-sm font-medium text-gray-600">Total Value</h3>
            </div>
            <p className="text-3xl font-bold text-gray-900">
              ₩{portfolio?.total_value.toLocaleString()}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="text-green-600" size={24} />
              <h3 className="text-sm font-medium text-gray-600">Total P&L</h3>
            </div>
            <p className={`text-3xl font-bold ${portfolio?.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              ₩{portfolio?.total_pnl.toLocaleString()}
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="text-purple-600" size={24} />
              <h3 className="text-sm font-medium text-gray-600">Return</h3>
            </div>
            <p className={`text-3xl font-bold ${portfolio?.total_pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {portfolio?.total_pnl_pct.toFixed(2)}%
            </p>
          </div>
        </div>

        {/* Holdings Table */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Holdings</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Shares</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Avg Price</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Current</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Value</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">P&L</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {portfolio?.holdings.map((holding) => (
                  <tr key={holding.ticker} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{holding.name}</div>
                      <div className="text-sm text-gray-500">{holding.ticker}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                      {holding.shares.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                      ₩{holding.avg_price.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                      ₩{holding.current_price.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                      ₩{holding.current_value.toLocaleString()}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-right text-sm font-medium ${
                      holding.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {holding.pnl >= 0 ? '+' : ''}₩{holding.pnl.toLocaleString()} ({holding.pnl_pct >= 0 ? '+' : ''}{holding.pnl_pct.toFixed(2)}%)
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Empty State */}
        {portfolio?.holdings.length === 0 && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <FileText className="mx-auto h-12 w-12 text-gray-400" size={48} />
            <h3 className="mt-4 text-lg font-medium text-gray-900">No holdings yet</h3>
            <p className="mt-2 text-sm text-gray-500">
              Add your first holding to start tracking your portfolio.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
