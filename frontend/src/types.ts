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

