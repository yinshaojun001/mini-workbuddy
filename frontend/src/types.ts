export interface ModelConfig {
  id: string; name: string; provider: 'deepseek' | 'qwen'; model: string; base_url: string;
  enabled: boolean; temperature: number; max_tokens: number; has_api_key: boolean; api_key_hint: string;
}
export interface Tool { id: string; name: string; description: string; enabled: boolean; approval_required: boolean }
export interface Skill { id: string; name: string; description: string; enabled: boolean; content?: string; tree?: TreeNode[]; updated_at: string }
export interface TreeNode { name: string; path: string; type: 'directory' | 'file'; children?: TreeNode[] }
export interface Agent { id: string; name: string; description: string; model_id: string; tool_ids: string[]; skill_ids: string[]; work_directory: string; enabled: boolean; is_builtin: boolean; updated_at: string }
export interface Session { id: string; agent_id: string; title: string; status: string; updated_at: string }
export interface Message { id: string; role: 'user' | 'assistant'; content: string; created_at: string }
export interface RunEvent { run_id: string; sequence: number; timestamp: string; type: string; data: Record<string, any> }
export interface RunSummary { id: string; session_id?: string; agent_id?: string; status: string; started_at: string; updated_at: string; event_count: number }
export type RuntimeAdapter = 'fortune' | 'dream'
export type PublishedAppHealth = 'ready' | 'disabled' | 'agent_unavailable' | 'model_unavailable' | 'adapter_unavailable' | 'reference_unavailable'
export interface PublishedApp {
  id: string; name: string; slug: string; agent_id: string; runtime_adapter: RuntimeAdapter; enabled: boolean;
  daily_limit: number; ttl_hours: number; max_questions: number;
  health: PublishedAppHealth;
  public_url: string; created_at: string; updated_at: string;
}

export type PublicRunStatus = 'active' | 'running' | 'completed' | 'failed' | 'expired'
export type PublicRunExecutionStatus = 'completed' | 'failed' | 'interrupted'
export type PublicRunMode = 'report' | 'question'
export type PublicRunErrorCode =
  | 'MODEL_TIMEOUT'
  | 'MODEL_AUTH_FAILED'
  | 'MODEL_RATE_LIMITED'
  | 'MODEL_RESPONSE_INVALID'
  | 'ENGINE_FAILED'
export type PublicRunEventType =
  | 'run.started'
  | 'agent.started'
  | 'model.started'
  | 'model.completed'
  | 'agent.completed'
  | 'run.completed'
  | 'model.failed'
  | 'agent.failed'
  | 'run.failed'

export interface PublicRunEvent {
  run_id: string
  sequence: number
  timestamp: string
  type: PublicRunEventType
  mode: PublicRunMode
  duration_ms: number
  model_id: string | null
  error_code: PublicRunErrorCode | null
}

export interface PublicRunGroup {
  run_id: string
  status: PublicRunExecutionStatus
  events: PublicRunEvent[]
}

export interface PublicRunSummary {
  session_id: string
  app_id: string
  app_name: string
  status: PublicRunStatus
  created_at: string
  updated_at: string
  expires_at: string
  remaining_questions: number
  message_count: number
  run_count: number
  last_run_status: PublicRunExecutionStatus | null
}

export interface PublicRunsListQuery {
  app_id?: string
  status?: PublicRunStatus
  query?: string
  limit?: number
  cursor?: string
}

export interface PublicRunsListResponse {
  items: PublicRunSummary[]
  next_cursor: string | null
  refreshed_at: string
}

export interface PublicRunBirth {
  name: string | null
  gender: string | null
  birth_date: string | null
  birth_time: string | null
  birth_time_unknown: boolean | null
  province_code: string | null
  city_code: string | null
  true_solar_time: boolean | null
  focus_topics: string[]
}

export interface PublicRunChartSummary {
  pillars: Partial<Record<'year' | 'month' | 'day' | 'hour', { gan_zhi: string }>>
  day_master: { gan?: string }
}

export interface PublicRunInputSummary {
  kind: 'fortune' | 'dream'
  fields: Record<string, unknown>
}

export interface PublicRunContextSummary {
  kind: 'fortune' | 'dream'
  summary: Record<string, unknown>
}

export interface PublicRunDetail {
  session: PublicRunSummary
  input: PublicRunInputSummary
  context: PublicRunContextSummary
  birth?: PublicRunBirth
  chart?: PublicRunChartSummary
  messages: Message[]
  runs: PublicRunGroup[]
  events: PublicRunEvent[]
  historical_events_unavailable: boolean
}

export interface PublicRunCounters {
  sessions_created: number
  reports_completed: number
  reports_failed: number
  questions_completed: number
  questions_failed: number
  runs_started: number
  runs_completed: number
  total_duration_ms: number
  average_duration_ms: number
  admin_deletions: number
  visitor_deletions: number
  ttl_cleanups: number
  errors: Partial<Record<PublicRunErrorCode, number>>
}

export interface PublicRunStats {
  version: number
  apps: Record<string, PublicRunCounters>
  total: PublicRunCounters
}
