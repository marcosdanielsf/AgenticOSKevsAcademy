import { Agent } from '../lib/api';

interface SquadCardProps {
  name: string;
  icon: string;
  color: string;
  agents: Agent[];
}

const squadInfo: Record<string, { description: string; gradient: string }> = {
  outbound: {
    description: 'Active Lead Hunt',
    gradient: 'from-blue-500 to-blue-700',
  },
  inbound: {
    description: 'Lead Processing',
    gradient: 'from-green-500 to-green-700',
  },
  infrastructure: {
    description: 'System Support',
    gradient: 'from-gray-500 to-gray-700',
  },
  security: {
    description: 'Protection & Compliance',
    gradient: 'from-red-500 to-red-700',
  },
  performance: {
    description: 'Optimization',
    gradient: 'from-yellow-500 to-orange-600',
  },
  quality: {
    description: 'Quality Assurance',
    gradient: 'from-purple-500 to-purple-700',
  },
};

export default function SquadCard({ name, icon, color, agents }: SquadCardProps) {
  const info = squadInfo[name] || { description: '', gradient: 'from-gray-500 to-gray-700' };
  const activeCount = agents.filter(a => a.state === 'running' || a.state === 'idle').length;
  const totalTasks = agents.reduce((sum, a) => sum + a.tasks_completed, 0);

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden hover:border-slate-600 transition-all duration-300 hover:shadow-lg hover:shadow-indigo-500/10">
      {/* Header */}
      <div className={`bg-gradient-to-r ${info.gradient} p-4`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{icon}</span>
            <div>
              <h3 className="text-lg font-bold capitalize">{name}</h3>
              <p className="text-xs text-white/70">{info.description}</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold">{agents.length}</div>
            <div className="text-xs text-white/70">agents</div>
          </div>
        </div>
      </div>

      {/* Agents List */}
      <div className="p-4 space-y-2">
        {agents.map((agent, idx) => (
          <div
            key={agent.name}
            className="flex items-center justify-between p-2 rounded-lg bg-slate-900/50 hover:bg-slate-900 transition-colors animate-slide-in"
            style={{ animationDelay: `${idx * 50}ms` }}
          >
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  agent.state === 'running'
                    ? 'bg-green-500 agent-active'
                    : agent.state === 'idle'
                    ? 'bg-green-500'
                    : 'bg-gray-500'
                }`}
              />
              <span className="text-sm font-medium">{agent.name}</span>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="text-slate-400">
                {agent.tasks_completed} tasks
              </span>
              <span
                className={`font-medium ${
                  agent.success_rate >= 0.9
                    ? 'text-green-400'
                    : agent.success_rate >= 0.7
                    ? 'text-yellow-400'
                    : 'text-red-400'
                }`}
              >
                {(agent.success_rate * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Footer Stats */}
      <div className="border-t border-slate-700 p-3 flex justify-between text-xs text-slate-400">
        <span>{activeCount}/{agents.length} active</span>
        <span>{totalTasks} total tasks</span>
      </div>
    </div>
  );
}
