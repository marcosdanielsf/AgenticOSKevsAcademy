import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import useSWR from 'swr';
import { fetchLogs, LogEntry } from '../lib/api';

const squadColors: Record<string, string> = {
  outbound: 'from-blue-500 to-blue-600',
  inbound: 'from-green-500 to-green-600',
  infrastructure: 'from-gray-500 to-gray-600',
  security: 'from-red-500 to-red-600',
  performance: 'from-yellow-500 to-orange-500',
  quality: 'from-purple-500 to-purple-600',
};

const levelColors: Record<string, string> = {
  info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  warning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  error: 'bg-red-500/20 text-red-400 border-red-500/30',
};

const levelIcons: Record<string, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  error: '❌',
};

export default function LogsPage() {
  const [selectedSquad, setSelectedSquad] = useState<string>('all');
  const [selectedLevel, setSelectedLevel] = useState<string>('all');

  const { data: logs, error, mutate } = useSWR<LogEntry[]>(
    'logs',
    fetchLogs,
    { refreshInterval: 2000 }
  );

  const squads = ['all', 'outbound', 'inbound', 'infrastructure', 'security', 'performance', 'quality'];
  const levels = ['all', 'info', 'warning', 'error'];

  // Filter logs based on selected filters
  const filteredLogs = logs?.filter((log) => {
    const squadMatch = selectedSquad === 'all' || log.squad === selectedSquad;
    const levelMatch = selectedLevel === 'all' || log.level === selectedLevel;
    return squadMatch && levelMatch;
  }) || [];

  return (
    <>
      <Head>
        <title>Real-Time Logs - Socialfy Dashboard</title>
      </Head>

      <div className="min-h-screen p-8">
        {/* Header */}
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-4 mb-2">
                <Link href="/">
                  <span className="text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer">
                    ← Back to Dashboard
                  </span>
                </Link>
              </div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                Real-Time Agent Logs
              </h1>
              <p className="text-slate-400 mt-1">Live activity monitoring • Auto-refresh every 2s</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="px-4 py-2 rounded-full text-sm font-medium bg-green-500/20 text-green-400 border border-green-500/30">
                ● Live
              </span>
              <span className="text-slate-400 text-sm">
                {filteredLogs.length} logs
              </span>
            </div>
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400">
            Failed to connect to logs API. Make sure the backend is running.
          </div>
        )}

        {/* Filters */}
        <div className="mb-6 bg-slate-800/50 rounded-xl border border-slate-700 p-6">
          <div className="flex flex-col md:flex-row gap-6">
            {/* Squad Filter */}
            <div className="flex-1">
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Filter by Squad
              </label>
              <div className="flex flex-wrap gap-2">
                {squads.map((squad) => (
                  <button
                    key={squad}
                    onClick={() => setSelectedSquad(squad)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 capitalize ${
                      selectedSquad === squad
                        ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/25'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {squad === 'all' ? '🌐 All Squads' : squad}
                  </button>
                ))}
              </div>
            </div>

            {/* Level Filter */}
            <div className="flex-1">
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Filter by Level
              </label>
              <div className="flex flex-wrap gap-2">
                {levels.map((level) => (
                  <button
                    key={level}
                    onClick={() => setSelectedLevel(level)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 capitalize ${
                      selectedLevel === level
                        ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/25'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {level === 'all' ? '📋 All Levels' : `${levelIcons[level]} ${level}`}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Logs Container */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
          <div className="border-b border-slate-700 p-4 bg-slate-900/50">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Activity Stream</h2>
              <button
                onClick={() => mutate()}
                className="px-3 py-1 rounded-lg text-xs font-medium bg-slate-700 hover:bg-slate-600 transition-colors"
              >
                🔄 Refresh
              </button>
            </div>
          </div>

          {/* Log Entries */}
          <div className="max-h-[700px] overflow-y-auto">
            {filteredLogs.length === 0 && !error && (
              <div className="flex items-center justify-center py-20">
                <div className="text-center">
                  <div className="text-6xl mb-4">📭</div>
                  <p className="text-slate-400">No logs found matching your filters</p>
                </div>
              </div>
            )}

            {!logs && !error && (
              <div className="flex items-center justify-center py-20">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
                  <p className="text-slate-400">Loading logs...</p>
                </div>
              </div>
            )}

            <div className="divide-y divide-slate-700">
              {filteredLogs.map((log, idx) => (
                <div
                  key={idx}
                  className="p-4 hover:bg-slate-900/30 transition-colors animate-slide-in"
                  style={{ animationDelay: `${idx * 20}ms` }}
                >
                  <div className="flex items-start gap-4">
                    {/* Timestamp */}
                    <div className="flex-shrink-0 w-32 text-xs text-slate-500 font-mono pt-1">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </div>

                    {/* Level Badge */}
                    <div className="flex-shrink-0">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium border ${
                          levelColors[log.level]
                        }`}
                      >
                        {levelIcons[log.level]} {log.level.toUpperCase()}
                      </span>
                    </div>

                    {/* Squad Badge */}
                    <div className="flex-shrink-0">
                      <span
                        className={`px-3 py-1 rounded-lg text-xs font-medium text-white bg-gradient-to-r ${
                          squadColors[log.squad] || 'from-gray-500 to-gray-600'
                        }`}
                      >
                        {log.squad}
                      </span>
                    </div>

                    {/* Agent Name */}
                    <div className="flex-shrink-0 min-w-[150px]">
                      <span className="text-sm font-medium text-slate-300">
                        {log.agent}
                      </span>
                    </div>

                    {/* Message */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-400 break-words">
                        {log.message}
                      </p>
                      {log.metadata && Object.keys(log.metadata).length > 0 && (
                        <div className="mt-2 p-2 bg-slate-900/50 rounded-lg">
                          <pre className="text-xs text-slate-500 overflow-x-auto">
                            {JSON.stringify(log.metadata, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-8 pt-6 border-t border-slate-800 text-center text-slate-500 text-sm">
          <p>Socialfy v1.0.0 | Real-Time Agent Activity Monitoring</p>
        </footer>
      </div>
    </>
  );
}
