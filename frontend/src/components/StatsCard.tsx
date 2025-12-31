interface StatsCardProps {
  title: string;
  value: string | number;
  icon: string;
  trend?: number;
  color?: string;
}

export default function StatsCard({ title, value, icon, trend, color = 'indigo' }: StatsCardProps) {
  const colorClasses: Record<string, string> = {
    indigo: 'from-indigo-500 to-indigo-600',
    green: 'from-green-500 to-green-600',
    yellow: 'from-yellow-500 to-orange-500',
    red: 'from-red-500 to-red-600',
    purple: 'from-purple-500 to-purple-600',
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 hover:border-slate-600 transition-all duration-300">
      <div className="flex items-center justify-between mb-4">
        <span className={`text-3xl p-3 rounded-xl bg-gradient-to-br ${colorClasses[color]} shadow-lg`}>
          {icon}
        </span>
        {trend !== undefined && (
          <span
            className={`text-sm font-medium px-2 py-1 rounded-full ${
              trend >= 0
                ? 'bg-green-500/20 text-green-400'
                : 'bg-red-500/20 text-red-400'
            }`}
          >
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </span>
        )}
      </div>
      <div>
        <p className="text-3xl font-bold mb-1">{value}</p>
        <p className="text-sm text-slate-400">{title}</p>
      </div>
    </div>
  );
}
