export type AppState = 'loading' | 'form' | 'chart_ready' | 'context_ready' | 'report_streaming' | 'report_ready' | 'question_streaming' | 'error'
export type PublicAppSlug = 'fortune' | 'dream'
export interface Location { code: string; parent_code: string; name: string; level: 'province' | 'city' }
export interface PublicMetadata { name: string; slug: PublicAppSlug; daily_limit: number; ttl_hours: number; max_questions: number; quota: { remaining: number; resets_at: string } }
export interface FortuneMetadata extends PublicMetadata { slug: 'fortune'; locations: Location[] }
export interface BirthPayload { name: string | null; gender: 'male' | 'female'; birth_date: string; birth_time: string | null; birth_time_unknown: boolean; province_code: string; city_code: string; true_solar_time: boolean; focus_topics: string[] }
export interface DreamPayload { dream_text: string; emotions: string[]; recurring: boolean; recent_context: string | null }
export interface DreamMetadata extends PublicMetadata { slug: 'dream'; form: { dream_text: { min_length: number; max_length: number }; emotions: { options: string[]; max_items: number }; recent_context: { max_length: number }; recurring: { type: 'boolean'; default: boolean } } }
export interface Pillar { stem: string; branch: string; ganZhi: string; stemTenGod: string; hiddenStems: Array<{ stem: string; tenGod: string; isMain: boolean }> }
export interface FortuneChart { input: BirthPayload; calculation_policy: Record<string, unknown>; pillars: { year: Pillar; month: Pillar; day: Pillar; hour: Pillar | null }; day_master: { char: string; element: string; polarity: string }; five_elements: Record<string, number>; ten_gods: Record<string, string>; hidden_stems: Record<string, unknown[]>; da_yun: { isForward: boolean; startAge: number; cycles: Array<{ ganZhi: string; startAge: number; endAge: number; stemTenGod: string }> }; interactions: Array<{ description: string }>; solar_time: { trueSolarTime: string } | null; attribution: { name: string; url: string } }
export interface DreamPublicContext { kind: 'dream'; summary: { emotions: string[]; recurring: boolean }; symbols: Array<{ id: string; label: string }>; reference_index_version: string }
export interface PublicMessage { id: string; role: 'user' | 'assistant'; content: string; created_at: string }
export interface SessionPayload { session: { id: string; status: string; expires_at: string; remaining_questions: number }; quota?: { daily_limit: number; remaining: number; resets_at: string }; context?: unknown; messages: PublicMessage[] }
export interface FortuneSessionPayload extends SessionPayload { chart: FortuneChart }
export interface DreamSessionPayload extends SessionPayload { context: DreamPublicContext }
export interface SseEvent { type: string; data: { content?: string; code?: string; message?: string } }
