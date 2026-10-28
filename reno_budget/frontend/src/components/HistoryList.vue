<script setup lang="ts">
import { dateTime, day, money, STATUS_LABELS, vatRate } from '@/format'
import { useAppStore } from '@/stores/app'
import { useDrawerStore } from '@/stores/drawer'
import type { AuditEntry, Stage } from '@/types'

/** Renders change-history entries with human-readable field names and values. */
const props = withDefaults(defineProps<{ entries: AuditEntry[]; showEntity?: boolean }>(), {
  showEntity: true,
})

const app = useAppStore()
const drawer = useDrawerStore()

const FIELD_LABELS: Record<string, string> = {
  title: 'Title',
  name: 'Name',
  description: 'Description',
  notes: 'Notes',
  note: 'Note',
  stage: 'Stage',
  amount_excl_cents: 'Amount excl. VAT',
  vat_cents: 'VAT',
  vat_rate: 'VAT rate',
  amount_cents: 'Amount',
  budget_cents: 'Budget',
  total_budget_cents: 'Total budget',
  contingency_pct: 'Contingency',
  category_id: 'Category',
  parent_id: 'Parent',
  room_id: 'Room',
  supplier_id: 'Supplier',
  milestone_id: 'Milestone',
  expense_date: 'Date',
  due_date: 'Due date',
  date: 'Date',
  planned_start: 'Planned start',
  planned_end: 'Planned end',
  actual_start: 'Actual start',
  actual_end: 'Actual end',
  quote_ref: 'Quote ref',
  invoice_no: 'Invoice no.',
  method: 'Method',
  reference: 'Reference',
  archived: 'Archived',
  kind: 'Kind',
  original_name: 'File name',
}
const HIDDEN = new Set(['stored_name', 'mime_type', 'size_bytes', 'uploaded_by', 'created_by', 'sort_order', 'expense_id'])

const ENTITY_LABELS: Record<string, string> = {
  expense: 'Expense',
  payment: 'Payment',
  attachment: 'Attachment',
  category: 'Category',
  room: 'Room',
  supplier: 'Supplier',
  milestone: 'Milestone',
  settings: 'Settings',
}

const ACTION: Record<string, { icon: string; verb: string }> = {
  create: { icon: 'pi pi-plus-circle', verb: 'created' },
  update: { icon: 'pi pi-pencil', verb: 'changed' },
  delete: { icon: 'pi pi-trash', verb: 'deleted' },
}

function formatValue(field: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (field.endsWith('_cents')) return money(value as number)
  if (field === 'vat_rate' || field === 'contingency_pct') return vatRate(value as number)
  if (field === 'stage') return STATUS_LABELS[value as Stage] ?? String(value)
  if (field === 'category_id' || field === 'parent_id') return app.categoryPath(value as number) || `#${value}`
  if (field === 'room_id') return app.roomById.get(value as number)?.name ?? `#${value}`
  if (field === 'supplier_id') return app.supplierById.get(value as number)?.name ?? `#${value}`
  if (field === 'milestone_id') return app.milestoneById.get(value as number)?.name ?? `#${value}`
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) return day(value)
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (Array.isArray(value)) return value.join(', ')
  return String(value)
}

function changes(entry: AuditEntry) {
  if (entry.action !== 'update') return []
  return Object.entries(entry.changes)
    .filter(([field]) => !HIDDEN.has(field))
    .map(([field, [from, to]]) => ({
      field: FIELD_LABELS[field] ?? field,
      from: formatValue(field, from),
      to: formatValue(field, to),
    }))
}

function label(entry: AuditEntry): string | null {
  if (entry.entity_type === 'payment') {
    const amount = entry.changes.amount_cents
    if (amount) return `of ${money((amount[1] ?? amount[0]) as number)}`
  }
  return entry.label
}

function openable(entry: AuditEntry) {
  return entry.expense_id !== null && entry.action !== 'delete'
}
</script>

<template>
  <div v-if="props.entries.length === 0" class="empty small">No changes recorded yet.</div>
  <ol v-else class="history">
    <li v-for="entry in props.entries" :key="entry.id">
      <i :class="ACTION[entry.action]?.icon" class="icon" />
      <div class="body">
        <div>
          <strong>{{ entry.user }}</strong>
          {{ ACTION[entry.action]?.verb }}
          <template v-if="props.showEntity">{{ (ENTITY_LABELS[entry.entity_type] ?? entry.entity_type).toLowerCase() }}</template>
          {{ ' ' }}
          <a
            v-if="label(entry) && openable(entry)"
            href="#"
            @click.prevent="drawer.open(entry.expense_id as number)"
          >{{ label(entry) }}</a>
          <span v-else-if="label(entry)">“{{ label(entry) }}”</span>
        </div>
        <ul v-if="changes(entry).length" class="changes">
          <li v-for="change in changes(entry)" :key="change.field">
            <span class="muted">{{ change.field }}:</span> {{ change.from }}
            <i class="pi pi-arrow-right" /> {{ change.to }}
          </li>
        </ul>
        <div class="muted small">{{ dateTime(entry.ts) }}</div>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.history {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.history > li {
  display: flex;
  gap: 10px;
}
.icon {
  color: var(--text-muted);
  margin-top: 2px;
}
.body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.changes {
  margin: 2px 0;
  padding-left: 0;
  list-style: none;
  font-size: 13px;
}
.changes .pi {
  font-size: 10px;
  color: var(--text-muted);
  margin: 0 2px;
}
</style>
