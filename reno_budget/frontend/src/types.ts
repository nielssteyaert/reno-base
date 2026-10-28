// Mirrors backend/app/schemas.py and the report payloads of backend/app/services/budget.py.
// All money is integer cents.

export type Stage = 'estimate' | 'quote' | 'ordered' | 'invoiced'
export type Status = Stage | 'paid'
export type PaymentStatus = 'unpaid' | 'partial' | 'paid'
export type Health = 'none' | 'ok' | 'warning' | 'over'
export type MilestoneStatus = 'planned' | 'in_progress' | 'done' | 'late'
export type AttachmentKind = 'quote' | 'invoice' | 'photo' | 'other'
export type PaymentMethod = 'bank_transfer' | 'card' | 'cash' | 'other'

export interface Settings {
  project_name: string
  currency: string
  locale: string
  total_budget_cents: number
  contingency_pct: number
  vat_rates: number[]
  default_vat_rate: number
  start_date: string | null
  target_end_date: string | null
}

export interface Category {
  id: number
  name: string
  parent_id: number | null
  color: string | null
  budget_cents: number | null
  sort_order: number
  archived: boolean
  notes: string | null
}

export interface Room {
  id: number
  name: string
  color: string | null
  budget_cents: number | null
  sort_order: number
  archived: boolean
  notes: string | null
}

export interface Supplier {
  id: number
  name: string
  contact_person: string | null
  phone: string | null
  email: string | null
  website: string | null
  address: string | null
  vat_number: string | null
  notes: string | null
  archived: boolean
}

export interface Milestone {
  id: number
  name: string
  room_id: number | null
  planned_start: string | null
  planned_end: string | null
  actual_start: string | null
  actual_end: string | null
  sort_order: number
  notes: string | null
  status: MilestoneStatus
}

export interface Payment {
  id: number
  expense_id: number
  date: string
  amount_cents: number
  method: PaymentMethod
  reference: string | null
  note: string | null
}

export interface Attachment {
  id: number
  expense_id: number
  kind: AttachmentKind
  original_name: string
  mime_type: string
  size_bytes: number
  uploaded_at: string
  uploaded_by: string | null
}

export interface Expense {
  id: number
  title: string
  description: string | null
  category_id: number | null
  room_id: number | null
  supplier_id: number | null
  milestone_id: number | null
  stage: Stage
  status: Status
  payment_status: PaymentStatus
  committed: boolean
  amount_excl_cents: number
  vat_rate: number
  vat_cents: number
  amount_incl_cents: number
  paid_cents: number
  outstanding_cents: number
  expense_date: string | null
  due_date: string | null
  quote_ref: string | null
  invoice_no: string | null
  notes: string | null
  attachment_count: number
  payment_count: number
  created_at: string
  updated_at: string
  created_by: string | null
}

export interface ExpenseDetail extends Expense {
  payments: Payment[]
  attachments: Attachment[]
}

export interface AuditEntry {
  id: number
  ts: string
  user: string
  entity_type: string
  entity_id: number
  expense_id: number | null
  action: 'create' | 'update' | 'delete'
  label: string | null
  changes: Record<string, [unknown, unknown]>
}

export interface BudgetLine {
  count: number
  excl: number
  vat: number
  incl: number
  estimated: number
  quoted: number
  committed: number
  paid: number
  outstanding: number
  forecast: number
  budget: number | null
  remaining: number | null
  pct_committed: number | null
  pct_forecast: number | null
  pct_paid: number | null
  health: Health
}

export interface NamedLine extends BudgetLine {
  id: number | null
  name: string
  color: string | null
  archived: boolean
  children?: NamedLine[]
  last_payment?: string | null
}

export interface Summary extends BudgetLine {
  contingency_pct: number
  contingency_reserve: number
  working_budget: number
  uses_contingency: boolean
  over_budget: boolean
  contingency_used: number
  allocated_budget: number
  unallocated_budget: number
  funnel: { status: Status; count: number; amount: number }[]
}

export interface Dashboard {
  summary: Summary
  categories: NamedLine[]
  rooms: NamedLine[]
  due: {
    id: number
    title: string
    due_date: string
    outstanding: number
    overdue: boolean
    supplier_id: number | null
  }[]
  milestones: {
    id: number
    name: string
    planned_start: string | null
    planned_end: string | null
    status: MilestoneStatus
  }[]
  recent: AuditEntry[]
}

export interface MonthRow {
  month: string
  paid: number
  committed: number
  cumulative_paid: number
  cumulative_committed: number
}

export interface ReportFilters {
  date_from?: string | null
  date_to?: string | null
  category_id?: number[]
  room_id?: number[]
  supplier_id?: number[]
  status?: Status[]
  q?: string | null
}

export interface BackupInfo {
  name: string
  size_bytes: number
  created_at: string | null
  reason: string | null
  app_version: string | null
  attachments: number | null
}
