import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import useSWR from 'swr';
import { fetchSystemHealth, SystemHealth, Agent } from '../lib/api';

interface TimeSeriesDataPoint {
  timestamp: string;
  tasks: number;
  success_rate: number;
}

interface SquadMetrics {
  name: string;
  total_tasks: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  agents: Agent[];
}

export default function Metrics() {
  const [timeSeriesData, setTimeSeriesData] = useState<TimeSeriesDataPoint[]>([]);

  const { data: health, error: fetchError } = useSWR<SystemHealth>(
    'system-health',
    fetchSystemHealth,
    { refreshInterval: 5000 }
  );

  // Collect time series data
  useEffect(() => {
    if (health) {
      setTimeSeriesData(prev => {
        const newDataPoint: TimeSeriesDataPoint = {
          timestamp: new Date().toLocaleTimeString(),
          tasks: health.total_tasks_processed,
          success_rate: health.overall_success_rate * 100,
        };

        // Keep only last 20 data points
        const updated = [...prev, newDataPoint].slice(-20);
        return updated;
      });
    }
  }, [health?.total_tasks_processed]);

  // Calculate squad metrics
  const squadMetrics: SquadMetrics[] = [];
  if (health?.agents) {
    const squadMap: Record<string, Agent[]> = {};

    Object.values(health.agents).forEach((agent) => {
      if (!squadMap[agent.squad]) {
        squadMap[agent.squad] = [];
      }
      squadMap[agent.squad].push(agent);
    });

    Object.entries(squadMap).forEach(([squadName, agents]) => {
      const total_tasks = agents.reduce((sum, a) => sum + a.tasks_completed + a.tasks_failed, 0);
      const success_count = agents.reduce((sum, a) => sum + a.tasks_completed, 0);
      const failure_count = agents.reduce((sum, a) => sum + a.tasks_failed, 0);

      squadMetrics.push({
        name: squadName,
        total_tasks,
        success_count,
        failure_count,
        success_rate: total_tasks > 0 ? (success_count / total_tasks) * 100 : 0,
        agents,
      });
    });
  }

  // Sort agents by performance
  const allAgents = health?.agents ? Object.values(health.agents) : [];
  const sortedAgents = [...allAgents].sort((a, b) => {
    const totalA = a.tasks_completed + a.tasks_failed;
    const totalB = b.tasks_completed + b.tasks_failed;
    if (totalA === 0 && totalB === 0) return 0;
    if (totalA === 0) return 1;
    if (totalB === 0) return -1;
    return b.success_rate - a.success_rate;
  });

  const maxTasks = Math.max(...timeSeriesData.map(d => d.tasks), 1);
  const maxSuccessRate = 100;

  return (
    <>
      <Head>
        <title>Metrics & Analytics - Socialfy</title>
      </Head>

      <div className="min-h-screen p-8">
        {/* Header */}
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <Link href="/" className="inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 transition-colors mb-2">
                <span>←</span> Back to Dashboard
              </Link>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                Metrics & Analytics
              </h1>
              <p className="text-slate-400 mt-1">Real-time system performance insights</p>
            </div>
            <div className="flex items-center gap-4">
              <span
                className={`px-4 py-2 rounded-full text-sm font-medium ${
                  health?.status === 'healthy'
                    ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                    : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                }`}
              >
                {health?.status === 'healthy' ? '● Live' : '● Degraded'}
              </span>
            </div>
          </div>
        </header>

        {/* Error Banner */}
        {fetchError && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400">
            Failed to connect to API. Make sure the backend is running.
          </div>
        )}

        {/* Task Processing Over Time */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <span>📈</span> Task Processing Over Time
          </h2>
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
            <div className="grid grid-cols-2 gap-8">
              {/* Tasks Chart */}
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-4">Total Tasks Processed</h3>
                <div className="h-48 flex items-end gap-1">
                  {timeSeriesData.map((point, idx) => (
                    <div key={idx} className="flex-1 flex flex-col items-center group">
                      <div className="relative w-full">
                        <div
                          className="bg-gradient-to-t from-indigo-500 to-indigo-400 rounded-t transition-all duration-300 hover:from-indigo-400 hover:to-indigo-300"
                          style={{
                            height: `${Math.max((point.tasks / maxTasks) * 180, 2)}px`,
                          }}
                        />
                        <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 bg-slate-900 px-2 py-1 rounded text-xs opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                          {point.tasks}
                        </div>
                      </div>
                      {idx % 5 === 0 && (
                        <span className="text-xs text-slate-500 mt-2 transform -rotate-45 origin-top-left">
                          {point.timestamp}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
                {timeSeriesData.length === 0 && (
                  <div className="h-48 flex items-center justify-center text-slate-500">
                    Collecting data...
                  </div>
                )}
              </div>

              {/* Success Rate Chart */}
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-4">Success Rate (%)</h3>
                <div className="h-48 flex items-end gap-1">
                  {timeSeriesData.map((point, idx) => (
                    <div key={idx} className="flex-1 flex flex-col items-center group">
                      <div className="relative w-full">
                        <div
                          className={`rounded-t transition-all duration-300 ${
                            point.success_rate >= 90
                              ? 'bg-gradient-to-t from-green-500 to-green-400 hover:from-green-400 hover:to-green-300'
                              : point.success_rate >= 70
                              ? 'bg-gradient-to-t from-yellow-500 to-yellow-400 hover:from-yellow-400 hover:to-yellow-300'
                              : 'bg-gradient-to-t from-red-500 to-red-400 hover:from-red-400 hover:to-red-300'
                          }`}
                          style={{
                            height: `${Math.max((point.success_rate / maxSuccessRate) * 180, 2)}px`,
                          }}
                        />
                        <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 bg-slate-900 px-2 py-1 rounded text-xs opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                          {point.success_rate.toFixed(1)}%
                        </div>
                      </div>
                      {idx % 5 === 0 && (
                        <span className="text-xs text-slate-500 mt-2 transform -rotate-45 origin-top-left">
                          {point.timestamp}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
                {timeSeriesData.length === 0 && (
                  <div className="h-48 flex items-center justify-center text-slate-500">
                    Collecting data...
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Squad Success/Failure Rates */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <span>🎯</span> Success/Failure Rates by Squad
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {squadMetrics.map((squad) => (
              <div
                key={squad.name}
                className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 hover:border-slate-600 transition-all duration-300"
              >
                <h3 className="text-lg font-bold capitalize mb-4 text-indigo-400">{squad.name}</h3>

                {/* Progress Bar */}
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-400">Success Rate</span>
                    <span className={`font-bold ${
                      squad.success_rate >= 90 ? 'text-green-400' :
                      squad.success_rate >= 70 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {squad.success_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-3 bg-slate-900 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        squad.success_rate >= 90
                          ? 'bg-gradient-to-r from-green-500 to-green-400'
                          : squad.success_rate >= 70
                          ? 'bg-gradient-to-r from-yellow-500 to-yellow-400'
                          : 'bg-gradient-to-r from-red-500 to-red-400'
                      }`}
                      style={{ width: `${squad.success_rate}%` }}
                    />
                  </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="bg-slate-900/50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-indigo-400">{squad.total_tasks}</div>
                    <div className="text-xs text-slate-500">Total</div>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-green-400">{squad.success_count}</div>
                    <div className="text-xs text-slate-500">Success</div>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-3">
                    <div className="text-2xl font-bold text-red-400">{squad.failure_count}</div>
                    <div className="text-xs text-slate-500">Failed</div>
                  </div>
                </div>

                {/* Agent Count */}
                <div className="mt-4 pt-4 border-t border-slate-700 text-sm text-slate-400 text-center">
                  {squad.agents.length} agents
                </div>
              </div>
            ))}
          </div>
          {squadMetrics.length === 0 && (
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-12 text-center text-slate-500">
              No squad data available
            </div>
          )}
        </div>

        {/* Agent Performance Comparison */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <span>🏆</span> Agent Performance Ranking
          </h2>
          <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-900/50">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Rank
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Agent Name
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Squad
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Tasks
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Success Rate
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                      Performance
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {sortedAgents.slice(0, 15).map((agent, idx) => {
                    const totalTasks = agent.tasks_completed + agent.tasks_failed;
                    const successRate = agent.success_rate * 100;

                    return (
                      <tr key={agent.name} className="hover:bg-slate-900/30 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {idx === 0 && <span className="text-2xl mr-2">🥇</span>}
                            {idx === 1 && <span className="text-2xl mr-2">🥈</span>}
                            {idx === 2 && <span className="text-2xl mr-2">🥉</span>}
                            <span className="text-sm font-medium text-slate-300">#{idx + 1}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <span
                              className={`w-2 h-2 rounded-full ${
                                agent.state === 'running'
                                  ? 'bg-green-500'
                                  : agent.state === 'idle'
                                  ? 'bg-green-500'
                                  : 'bg-gray-500'
                              }`}
                            />
                            <span className="text-sm font-medium">{agent.name}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 py-1 text-xs rounded-full bg-indigo-500/20 text-indigo-400 capitalize">
                            {agent.squad}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm">
                            <div className="font-medium text-slate-300">{totalTasks}</div>
                            <div className="text-xs text-slate-500">
                              {agent.tasks_completed}✓ / {agent.tasks_failed}✗
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`text-sm font-bold ${
                            successRate >= 90 ? 'text-green-400' :
                            successRate >= 70 ? 'text-yellow-400' : 'text-red-400'
                          }`}>
                            {successRate.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-full transition-all duration-500 ${
                                successRate >= 90
                                  ? 'bg-gradient-to-r from-green-500 to-green-400'
                                  : successRate >= 70
                                  ? 'bg-gradient-to-r from-yellow-500 to-yellow-400'
                                  : 'bg-gradient-to-r from-red-500 to-red-400'
                              }`}
                              style={{ width: `${successRate}%` }}
                            />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {sortedAgents.length === 0 && (
              <div className="p-12 text-center text-slate-500">
                No agent data available
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-12 pt-6 border-t border-slate-800 text-center text-slate-500 text-sm">
          <p>Socialfy Analytics | Updated every 5 seconds</p>
          <p className="mt-1">
            Last updated: {health?.timestamp ? new Date(health.timestamp).toLocaleString() : 'N/A'}
          </p>
        </footer>
      </div>
    </>
  );
}
