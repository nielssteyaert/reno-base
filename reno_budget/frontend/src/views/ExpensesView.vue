<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import DatePicker from 'primevue/datepicker'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api, download } from '@/api'
import StatusTag from '@/components/StatusTag.vue'
import { useConfirmDelete, useNotify } from '@/composables'
import { day, money, PAYMENT_STATUS_LABELS, STAGE_OPTIONS, STATUS_OPTIONS, toIsoDate, vatRate } from '@/format'
import { useAppStore } from '@/stores/app'
import { useDrawerStore } from '@/stores/drawer'
import type { Expense, Status } from '@/types'

const app = useAppStore()
const drawer = useDrawerStore()
const route = useRoute()
const notify = useNotify()
const confirmDelete = useConfirmDelete()

const expenses = ref<Expense[]>([])
const loading = ref(true)
const selection = ref<Expense[]>([])

// Filters
const search = ref('')
const categoryIds = ref<number[]>([])
const roomIds = ref<number[]>([])
const supplierIds = ref<number[]>([])
const statuses = ref<Status[]>([])
const paymentStatuses = ref<string[]>([])
const dateRange = ref<Date[] | null>(null)

const paymentStatusOptions = Object.entries(PAYMENT_STATUS_LABELS).map(([value, label]) => ({ value, label }))

const optionalColumns = [
  { key: 'room', label: 'Room' },
  { key: 'supplier', label: 'Supplier' },
  { key: 'milestone', label: 'Milestone' },
  { key: 'excl', label: 'Excl. VAT' },
  { key: 'vat', label: 'VAT' },
  { key: 'paid', label: 'Paid' },
  { key: 'outstanding', label: 'Outstanding' },
  { key: 'due', label: 'Due date' },
  { key: 'refs', label: 'Quote / invoice' },
]
const COLUMNS_KEY = 'reno-expense-columns'
function loadColumns(): string[] {
  try {
    const stored = JSON.parse(localStorage.getItem(COLUMNS_KEY) ?? 'null')
    if (Array.isArray(stored)) return stored
  } catch {
    // ignore
  }
  return ['room', 'supplier', 'paid', 'outstanding']
}
const visibleColumns = ref<string[]>(loadColumns())
watch(visibleColumns, (value) => {
  try {
    localStorage.setItem(COLUMNS_KEY, JSON.stringify(value))
  } catch {
    // ignore
  }
})
const show = (key: string) => visibleColumns.value.includes(key)

async function load() {
  loading.value = true
  try {
    expenses.value = await api.get<Expense[]>('expenses')
    const ids = new Set(expenses.value.map((e) => e.id))
    selection.value = selection.value.filter((e) => ids.has(e.id))
  } catch (error) {
    notify.error(error, 'Could not load expenses')
  } finally {
    loading.value = false
  }
}

const expandedCategories = computed(() => {
  const ids = new Set(categoryIds.value)
  for (const c of app.categories) if (c.parent_id !== null && ids.has(c.parent_id)) ids.add(c.id)
  return ids
})

const filtered = computed(() => {
  const needle = search.value.trim().toLowerCase()
  const [from, to] = dateRange.value ?? []
  const fromIso = from ? toIsoDate(from) : null
  const toIso = to ? toIsoDate(to) : fromIso
  return expenses.value.filter((e) => {
    if (categoryIds.value.length && !expandedCategories.value.has(e.category_id ?? -1)) return false
    if (roomIds.value.length && !roomIds.value.includes(e.room_id ?? -1)) return false
    if (supplierIds.value.length && !supplierIds.value.includes(e.supplier_id ?? -1)) return false
    if (statuses.value.length && !statuses.value.includes(e.status)) return false
    if (paymentStatuses.value.length && !paymentStatuses.value.includes(e.payment_status)) return false
    if (fromIso && (!e.expense_date || e.expense_date < fromIso)) return false
    if (toIso && (!e.expense_date || e.expense_date > toIso)) return false
    if (needle) {
      const haystack = [
        e.title,
        e.description,
        e.notes,
        e.quote_ref,
        e.invoice_no,
        app.supplierById.get(e.supplier_id ?? -1)?.name,
        app.categoryPath(e.category_id),
        app.roomById.get(e.room_id ?? -1)?.name,
      ]
      if (!haystack.some((v) => v && v.toLowerCase().includes(needle))) return false
    }
    return true
  })
})

const totals = computed(() =>
  filtered.value.reduce(
    (t, e) => ({
      excl: t.excl + e.amount_excl_cents,
      vat: t.vat + e.vat_cents,
      incl: t.incl + e.amount_incl_cents,
      paid: t.paid + e.paid_cents,
      outstanding: t.outstanding + e.outstanding_cents,
    }),
    { excl: 0, vat: 0, incl: 0, paid: 0, outstanding: 0 },
  ),
)

const hasFilters = computed(
  () =>
    !!search.value ||
    categoryIds.value.length > 0 ||
    roomIds.value.length > 0 ||
    supplierIds.value.length > 0 ||
    statuses.value.length > 0 ||
    paymentStatuses.value.length > 0 ||
    !!dateRange.value,
)

function clearFilters() {
  search.value = ''
  categoryIds.value = []
  roomIds.value = []
  supplierIds.value = []
  statuses.value = []
  paymentStatuses.value = []
  dateRange.value = null
}

function applyRouteQuery() {
  const q = route.query
  const ids = (v: unknown) => [v].flat().filter(Boolean).map(Number)
  if (q.category) categoryIds.value = ids(q.category)
  if (q.room) roomIds.value = ids(q.room)
  if (q.supplier) supplierIds.value = ids(q.supplier)
  if (q.status) statuses.value = [q.status].flat() as Status[]
  if (q.open) drawer.open(Number(q.open))
}

// Sort helpers so the table sorts by name rather than id.
const rows = computed(() =>
  filtered.value.map((e) => ({
    ...e,
    _category: app.categoryPath(e.category_id),
    _room: app.roomById.get(e.room_id ?? -1)?.name ?? '',
    _supplier: app.supplierById.get(e.supplier_id ?? -1)?.name ?? '',
    _milestone: app.milestoneById.get(e.milestone_id ?? -1)?.name ?? '',
  })),
)

async function exportView() {
  try {
    await download('export/expenses', { body: { ids: filtered.value.map((e) => e.id) }, fallback: 'expenses.xlsx' })
  } catch (error) {
    notify.error(error, 'Export failed')
  }
}

// Bulk editing
const bulkVisible = ref(false)
const bulkField = ref<string>('category_id')
const bulkValue = ref<number | string | null>(null)
const bulkFields = [
  { value: 'category_id', label: 'Category' },
  { value: 'room_id', label: 'Room' },
  { value: 'supplier_id', label: 'Supplier' },
  { value: 'milestone_id', label: 'Milestone' },
  { value: 'stage', label: 'Stage' },
  { value: 'vat_rate', label: 'VAT rate' },
]
const bulkOptions = computed(() => {
  switch (bulkField.value) {
    case 'category_id':
      return app.categoryOptions()
    case 'room_id':
      return app.activeRooms.map((r) => ({ value: r.id, label: r.name }))
    case 'supplier_id':
      return app.activeSuppliers.map((s) => ({ value: s.id, label: s.name }))
    case 'milestone_id':
      return app.milestones.map((m) => ({ value: m.id, label: m.name }))
    case 'stage':
      return STAGE_OPTIONS
    default:
      return (app.settings?.vat_rates ?? []).map((r) => ({ value: r, label: vatRate(r) }))
  }
})
const bulkClearable = computed(() => bulkField.value.endsWith('_id'))
watch(bulkField, () => (bulkValue.value = null))

async function applyBulk() {
  if (bulkValue.value === null && !bulkClearable.value) return
  try {
    const result = await api.post<{ affected: number }>('expenses/bulk', {
      ids: selection.value.map((e) => e.id),
      action: 'update',
      changes: { [bulkField.value]: bulkValue.value },
    })
    notify.success(`Updated ${result.affected} expense(s)`)
    bulkVisible.value = false
    app.touch()
  } catch (error) {
    notify.error(error, 'Bulk update failed')
  }
}

function bulkDelete() {
  const ids = selection.value.map((e) => e.id)
  confirmDelete(`Delete ${ids.length} expense(s) including their payments and files?`, async () => {
    try {
      await api.post('expenses/bulk', { ids, action: 'delete' })
      selection.value = []
      app.touch()
      notify.success(`Deleted ${ids.length} expense(s)`)
    } catch (error) {
      notify.error(error, 'Bulk delete failed')
    }
  })
}

watch(() => app.dataVersion, load)
watch(() => route.query, applyRouteQuery)
onMounted(() => {
  load()
  applyRouteQuery()
})
</script>

<template>
  <div class="toolbar">
    <IconField>
      <InputIcon class="pi pi-search" />
      <InputText v-model="search" placeholder="Search title, supplier, invoice…" />
    </IconField>
    <MultiSelect
      v-model="categoryIds"
      :options="app.categoryOptions()"
      option-label="label"
      option-value="value"
      placeholder="Category"
      filter
      :max-selected-labels="1"
      selected-items-label="{0} categories"
    />
    <MultiSelect
      v-model="roomIds"
      :options="app.rooms"
      option-label="name"
      option-value="id"
      placeholder="Room"
      :max-selected-labels="1"
      selected-items-label="{0} rooms"
    />
    <MultiSelect
      v-model="supplierIds"
      :options="app.suppliers"
      option-label="name"
      option-value="id"
      placeholder="Supplier"
      filter
      :max-selected-labels="1"
      selected-items-label="{0} suppliers"
    />
    <MultiSelect
      v-model="statuses"
      :options="STATUS_OPTIONS"
      option-label="label"
      option-value="value"
      placeholder="Status"
      :max-selected-labels="2"
    />
    <MultiSelect
      v-model="paymentStatuses"
      :options="paymentStatusOptions"
      option-label="label"
      option-value="value"
      placeholder="Payment"
      :max-selected-labels="1"
    />
    <DatePicker
      v-model="dateRange"
      selection-mode="range"
      :manual-input="false"
      placeholder="Date range"
      show-button-bar
      date-format="dd/mm/yy"
      style="width: 210px"
    />
    <Button v-if="hasFilters" label="Clear" icon="pi pi-filter-slash" text @click="clearFilters" />
    <span class="spacer" />
    <Button label="New expense" icon="pi pi-plus" @click="drawer.create()" />
  </div>

  <div class="card table-card">
    <div class="table-head">
      <div class="summary">
        <strong>{{ filtered.length }}</strong> expense(s) ·
        incl. VAT <strong>{{ money(totals.incl) }}</strong> ·
        paid <strong>{{ money(totals.paid) }}</strong> ·
        outstanding <strong>{{ money(totals.outstanding) }}</strong>
      </div>
      <div class="row">
        <template v-if="selection.length">
          <span class="muted small">{{ selection.length }} selected</span>
          <Button label="Edit selected" icon="pi pi-pencil" size="small" severity="secondary" outlined @click="bulkVisible = true" />
          <Button label="Delete" icon="pi pi-trash" size="small" severity="danger" outlined @click="bulkDelete" />
        </template>
        <MultiSelect
          v-model="visibleColumns"
          :options="optionalColumns"
          option-label="label"
          option-value="key"
          size="small"
          placeholder="Columns"
          :max-selected-labels="0"
          selected-items-label="Columns"
          aria-label="Visible columns"
        />
        <Button
          v-tooltip.top="'Export the expenses shown to Excel'"
          label="Excel"
          icon="pi pi-file-excel"
          size="small"
          severity="secondary"
          outlined
          :disabled="!filtered.length"
          @click="exportView"
        />
      </div>
    </div>

    <DataTable
      v-model:selection="selection"
      :value="rows"
      data-key="id"
      :loading="loading"
      paginator
      :rows="25"
      :rows-per-page-options="[25, 50, 100, 500]"
      sort-field="expense_date"
      :sort-order="-1"
      removable-sort
      size="small"
      scrollable
      :row-class="() => 'row-clickable'"
      @row-click="drawer.open(($event.data as Expense).id)"
    >
      <template #empty>
        <div class="empty">
          <i class="pi pi-receipt" />
          <template v-if="hasFilters">No expenses match these filters.</template>
          <template v-else>No expenses yet. Add your first one, or import a spreadsheet.</template>
        </div>
      </template>
      <Column selection-mode="multiple" style="width: 40px" />
      <Column field="expense_date" header="Date" sortable style="white-space: nowrap">
        <template #body="{ data }">{{ day(data.expense_date) }}</template>
      </Column>
      <Column field="title" header="Title" sortable style="min-width: 200px">
        <template #body="{ data }">
          <div class="title-cell">
            <span>{{ data.title }}</span>
            <i v-if="data.attachment_count" v-tooltip.top="`${data.attachment_count} file(s)`" class="pi pi-paperclip muted" />
          </div>
          <div v-if="data.description" class="muted small clamp">{{ data.description }}</div>
        </template>
      </Column>
      <Column field="_category" header="Category" sortable />
      <Column v-if="show('room')" field="_room" header="Room" sortable />
      <Column v-if="show('supplier')" field="_supplier" header="Supplier" sortable />
      <Column v-if="show('milestone')" field="_milestone" header="Milestone" sortable />
      <Column field="status" header="Status" sortable>
        <template #body="{ data }"><StatusTag :status="data.status" /></template>
      </Column>
      <Column v-if="show('excl')" field="amount_excl_cents" header="Excl. VAT" sortable class="num">
        <template #body="{ data }">{{ money(data.amount_excl_cents) }}</template>
      </Column>
      <Column v-if="show('vat')" field="vat_cents" header="VAT" sortable class="num">
        <template #body="{ data }">
          <span v-tooltip.top="vatRate(data.vat_rate)">{{ money(data.vat_cents) }}</span>
        </template>
      </Column>
      <Column field="amount_incl_cents" header="Incl. VAT" sortable class="num">
        <template #body="{ data }"><strong>{{ money(data.amount_incl_cents) }}</strong></template>
      </Column>
      <Column v-if="show('paid')" field="paid_cents" header="Paid" sortable class="num">
        <template #body="{ data }">{{ money(data.paid_cents) }}</template>
      </Column>
      <Column v-if="show('outstanding')" field="outstanding_cents" header="Outstanding" sortable class="num">
        <template #body="{ data }">{{ data.outstanding_cents ? money(data.outstanding_cents) : '—' }}</template>
      </Column>
      <Column v-if="show('due')" field="due_date" header="Due" sortable>
        <template #body="{ data }">{{ day(data.due_date) }}</template>
      </Column>
      <Column v-if="show('refs')" header="Quote / invoice">
        <template #body="{ data }">
          <span class="small">{{ [data.quote_ref, data.invoice_no].filter(Boolean).join(' / ') || '—' }}</span>
        </template>
      </Column>
    </DataTable>
  </div>

  <Dialog v-model:visible="bulkVisible" header="Edit selected expenses" modal :style="{ width: '420px' }">
    <div class="stack">
      <p class="muted" style="margin: 0">Change one field on {{ selection.length }} expense(s).</p>
      <div class="field">
        <label>Field</label>
        <Select v-model="bulkField" :options="bulkFields" option-label="label" option-value="value" />
      </div>
      <div class="field">
        <label>New value</label>
        <Select
          v-model="bulkValue"
          :options="bulkOptions"
          option-label="label"
          option-value="value"
          filter
          :show-clear="bulkClearable"
          :placeholder="bulkClearable ? 'None (clear the field)' : 'Choose a value'"
        />
        <span v-if="bulkField === 'vat_rate'" class="hint">Amounts excl. VAT stay the same; VAT is recalculated.</span>
      </div>
    </div>
    <template #footer>
      <Button label="Cancel" severity="secondary" outlined @click="bulkVisible = false" />
      <Button label="Apply" icon="pi pi-check" :disabled="bulkValue === null && !bulkClearable" @click="applyBulk" />
    </template>
  </Dialog>
</template>

<style scoped>
.table-card {
  padding: 0;
  overflow: hidden;
}
.table-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}
.summary {
  color: var(--text-2);
}
.title-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 550;
}
.clamp {
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
