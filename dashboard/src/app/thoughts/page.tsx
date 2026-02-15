"use client";

import { useState, useEffect } from "react";
import { Brain, Search, Plus, Trash2 } from "lucide-react";

interface Thought {
  id: string;
  content: string;
  thought_type: string;
  tags: string[];
  related_tickers: string[];
  confidence?: number;
  outcome?: string;
  created_at: string;
}

export default function ThoughtsPage() {
  const [thoughts, setThoughts] = useState<Thought[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewThought, setShowNewThought] = useState(false);
  const [newThought, setNewThought] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Thought[]>([]);

  useEffect(() => {
    fetchThoughts();
  }, []);

  const fetchThoughts = async () => {
    try {
      const response = await fetch("http://localhost:3000/api/thoughts/");
      if (response.ok) {
        const data = await response.json();
        setThoughts(data);
      }
    } catch (error) {
      console.error("Error fetching thoughts:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      const response = await fetch("http://localhost:3000/api/thoughts/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery }),
      });
      if (response.ok) {
        const data = await response.json();
        setSearchResults(data);
      }
    } catch (error) {
      console.error("Error searching thoughts:", error);
    }
  };

  const handleSubmitThought = async () => {
    if (!newThought.trim()) return;

    try {
      const response = await fetch("http://localhost:3000/api/thoughts/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: newThought,
          thought_type: "general",
        }),
      });

      if (response.ok) {
        setNewThought("");
        setShowNewThought(false);
        fetchThoughts();
      }
    } catch (error) {
      console.error("Error creating thought:", error);
    }
  };

  const handleDeleteThought = async (id: string) => {
    try {
      const response = await fetch(`http://localhost:3000/api/thoughts/${id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        fetchThoughts();
      }
    } catch (error) {
      console.error("Error deleting thought:", error);
    }
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      market_view: "bg-blue-100 text-blue-800",
      stock_idea: "bg-green-100 text-green-800",
      risk_concern: "bg-red-100 text-red-800",
      ai_insight: "bg-purple-100 text-purple-800",
      content_note: "bg-yellow-100 text-yellow-800",
      general: "bg-gray-100 text-gray-800",
    };
    return colors[type] || "bg-gray-100 text-gray-800";
  };

  const displayThoughts = searchQuery.trim() ? searchResults : thoughts;

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
          <Brain className="w-8 h-8" />
          생각 기록
        </h1>
        <button
          onClick={() => setShowNewThought(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-700 transition"
        >
          <Plus className="w-5 h-5" />
          새 생각
        </button>
      </div>

      {/* Search Bar */}
      <div className="mb-6 flex gap-2">
        <input
          type="text"
          placeholder="생각 검색..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSearch}
          className="bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-900 transition"
        >
          <Search className="w-5 h-5" />
        </button>
      </div>

      {/* New Thought Modal */}
      {showNewThought && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-lg">
            <h2 className="text-xl font-bold mb-4">새 생각 기록</h2>
            <textarea
              value={newThought}
              onChange={(e) => setNewThought(e.target.value)}
              placeholder="생각을 입력하세요..."
              className="w-full h-40 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  setShowNewThought(false);
                  setNewThought("");
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
              >
                취소
              </button>
              <button
                onClick={handleSubmitThought}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                저장
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Thoughts List */}
      <div className="space-y-4">
        {displayThoughts.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            {searchQuery.trim() ? "검색 결과가 없습니다." : "생각이 아직 없습니다."}
          </div>
        ) : (
          displayThoughts.map((thought) => (
            <div
              key={thought.id}
              className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm hover:shadow-md transition"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${getTypeColor(
                      thought.thought_type
                    )}`}
                  >
                    {thought.thought_type}
                  </span>
                  <span className="text-gray-500 text-sm">
                    {new Date(thought.created_at).toLocaleString("ko-KR")}
                  </span>
                </div>
                <button
                  onClick={() => handleDeleteThought(thought.id)}
                  className="text-gray-400 hover:text-red-600 transition"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
              <p className="text-gray-800 mb-3">{thought.content}</p>
              {thought.tags && thought.tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {thought.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
              {thought.related_tickers && thought.related_tickers.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {thought.related_tickers.map((ticker, index) => (
                    <span
                      key={index}
                      className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-sm font-medium"
                    >
                      {ticker}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
