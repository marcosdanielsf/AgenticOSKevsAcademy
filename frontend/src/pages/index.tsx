import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import useSWR from 'swr';
import SquadCard from '../components/SquadCard';
import StatsCard from '../components/StatsCard';
import { fetchSystemHealth, SystemHealth, Agent } from '../lib/api';

const squadIcons: Record<string, string> = {
  outbound: '🎯',
  inbound: '📥',
  infrastructure: '⚙️',
  security: '🛡️',
  performance: '⚡',
  quality: '✅',
};

export default function Dashboard() {
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: health, error: fetchError, mutate } = useSWR<SystemHealth>(
    'system-health',
    fetchSystemHealth,
    { refreshInterval: 5000 }
  );

  // Group agents by squad
  const squadAgents: Record<string, Agent[]> = {};
  if (health?.agents) {
    Object.values(health.agents).forEach((agent) => {
      if (!squadAgents[agent.squad]) {
        squadAgents[agent.squad] = [];
      }
      squadAgents[agent.squad].push(agent);
    });
  }

  const squadOrder = ['outbound', 'inbound', 'infrastructure', 'security', 'performance', 'quality'];

  const handleStartPipeline = async () => {
    try {
      setIsRunning(true);
      // TODO: Implement actual pipeline start
      // await startPipeline();
    } catch (e) {
      setError('Failed to start pipeline');
      setIsRunning(false);
    }
  };

  const handleStopPipeline = async () => {
    try {
      setIsRunning(false);
      // TODO: Implement actual pipeline stop
      // await stopPipeline();
    } catch (e) {
      setError('Failed to stop pipeline');
    }
  };

  return (
    <>
      <Head>
        <title>Socialfy Dashboard</title>
      </Head>

      <div className="min-h-screen p-8">
        {/* Header */}
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                SOCIALFY
              </h1>
              <p className="text-slate-400 mt-1">Lead Generation & DM Automation</p>
            </div>
            <div className="flex items-center gap-4">
              <Link
                href="/logs"
                className="px-4 py-2 rounded-xl font-medium bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-slate-600 text-slate-300 transition-all duration-300 flex items-center gap-2"
              >
                <span>📋</span> Logs
              </Link>
              <Link
                href="/metrics"
                className="px-4 py-2 rounded-xl font-medium bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-slate-600 text-slate-300 transition-all duration-300 flex items-center gap-2"
              >
                <span>📊</span> Metrics
              </Link>
              <span
                className={`px-4 py-2 rounded-full text-sm font-medium ${
                  health?.status === 'healthy'
                    ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                    : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                }`}
              >
                {health?.status === 'healthy' ? '● System Healthy' : '● System Degraded'}
              </span>
              <button
                onClick={isRunning ? handleStopPipeline : handleStartPipeline}
                className={`px-6 py-3 rounded-xl font-medium transition-all duration-300 ${
                  isRunning
                    ? 'bg-red-500 hover:bg-red-600 text-white'
                    : 'bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white shadow-lg shadow-indigo-500/25'
                }`}
              >
                {isRunning ? '⏹ Stop Pipeline' : '▶ Start Pipeline'}
              </button>
            </div>
          </div>
        </header>

        {/* Error Banner */}
        {(error || fetchError) && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400">
            {error || 'Failed to connect to API. Make sure the backend is running.'}
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          <StatsCard
            icon="🤖"
            title="Active Agents"
            value={health?.system_metrics?.active_agents || 0}
            color="indigo"
          />
          <StatsCard
            icon="📊"
            title="Tasks Processed"
            value={health?.total_tasks_processed || 0}
            color="green"
          />
          <StatsCard
            icon="✅"
            title="Success Rate"
            value={`${((health?.overall_success_rate || 0) * 100).toFixed(1)}%`}
            color="purple"
          />
          <StatsCard
            icon="🔄"
            title="Active Workflows"
            value={health?.active_workflows || 0}
            color="yellow"
          />
          <StatsCard
            icon="❌"
            title="Total Errors"
            value={health?.total_errors || 0}
            color="red"
          />
        </div>

        {/* Squads Grid */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <span>🏢</span> Agent Squads
            <span className="text-sm font-normal text-slate-400">
              ({Object.keys(squadAgents).length} squads, {Object.values(squadAgents).flat().length} agents)
            </span>
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {squadOrder.map((squadName) => {
            const agents = squadAgents[squadName] || [];
            if (agents.length === 0) return null;
            return (
              <SquadCard
                key={squadName}
                name={squadName}
                icon={squadIcons[squadName] || '📦'}
                color=""
                agents={agents}
              />
            );
          })}
        </div>

        {/* Loading State */}
        {!health && !fetchError && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
              <p className="text-slate-400">Connecting to Socialfy...</p>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-12 pt-6 border-t border-slate-800 text-center text-slate-500 text-sm">
          <p>Socialfy v1.0.0 | Multi-Agent Lead Generation System</p>
          <p className="mt-1">
            Last updated: {health?.timestamp ? new Date(health.timestamp).toLocaleString() : 'N/A'}
          </p>
        </footer>
      </div>
    </>
  );
}
