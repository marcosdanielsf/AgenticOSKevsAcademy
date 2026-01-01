const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export interface Agent {
  name: string;
  squad: string;
  state: string;
  tasks_completed: number;
  tasks_failed: number;
  success_rate: number;
}

export interface SystemHealth {
  status: string;
  timestamp: string;
  system_metrics: {
    total_tasks_routed: number;
    active_agents: number;
    workflows_completed: number;
    workflows_failed: number;
  };
  total_tasks_processed: number;
  total_errors: number;
  overall_success_rate: number;
  agents: Record<string, Agent>;
  active_workflows: number;
}

export interface LeadStats {
  total_leads: number;
  hot_leads: number;
  warm_leads: number;
  cold_leads: number;
  spam_leads: number;
  pending_leads: number;
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to fetch system health');
  return res.json();
}

export async function fetchLeadStats(tenantId: string): Promise<LeadStats> {
  const res = await fetch(`${API_BASE}/leads/stats?tenant_id=${tenantId}`);
  if (!res.ok) throw new Error('Failed to fetch lead stats');
  return res.json();
}

export async function processLead(username: string, tenantId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/leads/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, tenant_id: tenantId }),
  });
  if (!res.ok) throw new Error('Failed to process lead');
  return res.json();
}

export async function startPipeline(): Promise<any> {
  const res = await fetch(`${API_BASE}/pipeline/start`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to start pipeline');
  return res.json();
}

export async function stopPipeline(): Promise<any> {
  const res = await fetch(`${API_BASE}/pipeline/stop`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to stop pipeline');
  return res.json();
}

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error';
  squad: string;
  agent: string;
  message: string;
  metadata?: Record<string, any>;
}

// Mock data generator for logs (replace with actual API call when backend is ready)
export async function fetchLogs(): Promise<LogEntry[]> {
  // Simulate API call delay
  await new Promise(resolve => setTimeout(resolve, 100));

  const squads = ['outbound', 'inbound', 'infrastructure', 'security', 'performance', 'quality'];
  const levels: Array<'info' | 'warning' | 'error'> = ['info', 'info', 'info', 'warning', 'error'];
  const agents = {
    outbound: ['LeadScraperAgent', 'ProfileAnalyzerAgent', 'OutreachAgent'],
    inbound: ['LeadQualifierAgent', 'ResponseHandlerAgent', 'DataEnricherAgent'],
    infrastructure: ['DatabaseAgent', 'CacheAgent', 'QueueAgent'],
    security: ['AuthAgent', 'RateLimitAgent', 'ValidationAgent'],
    performance: ['MetricsAgent', 'OptimizationAgent', 'MonitoringAgent'],
    quality: ['TestAgent', 'AuditAgent', 'ComplianceAgent'],
  };

  const messages = {
    info: [
      'Successfully processed lead data',
      'Connected to external API',
      'Task completed successfully',
      'Database query executed',
      'Cache hit for request',
      'Message sent to queue',
      'Health check passed',
      'Started processing batch',
      'Completed workflow step',
      'Initialized connection pool',
    ],
    warning: [
      'API rate limit approaching threshold',
      'Response time exceeded 2 seconds',
      'Retry attempt 2 of 3',
      'Cache miss - fetching from database',
      'Queue processing delayed',
      'Memory usage above 70%',
      'Stale data detected in cache',
    ],
    error: [
      'Failed to connect to external API',
      'Database connection timeout',
      'Task execution failed',
      'Invalid data format received',
      'Authentication failed',
      'Message processing error',
      'Critical resource unavailable',
    ],
  };

  // Generate 50 mock log entries with recent timestamps
  const mockLogs: LogEntry[] = [];
  const now = Date.now();

  for (let i = 0; i < 50; i++) {
    const squad = squads[Math.floor(Math.random() * squads.length)];
    const level = levels[Math.floor(Math.random() * levels.length)];
    const agent = agents[squad as keyof typeof agents][
      Math.floor(Math.random() * agents[squad as keyof typeof agents].length)
    ];
    const message = messages[level][Math.floor(Math.random() * messages[level].length)];

    // Create timestamps going back from now (most recent first)
    const timestamp = new Date(now - i * 3000).toISOString();

    const log: LogEntry = {
      timestamp,
      level,
      squad,
      agent,
      message,
    };

    // Add metadata for some logs
    if (Math.random() > 0.7) {
      log.metadata = {
        task_id: `task_${Math.floor(Math.random() * 10000)}`,
        duration_ms: Math.floor(Math.random() * 5000),
        ...(level === 'error' && { error_code: `ERR_${Math.floor(Math.random() * 999)}` }),
      };
    }

    mockLogs.push(log);
  }

  return mockLogs;

  // When backend is ready, replace above with:
  // const res = await fetch(`${API_BASE}/logs`);
  // if (!res.ok) throw new Error('Failed to fetch logs');
  // return res.json();
}
