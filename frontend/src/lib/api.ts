const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
