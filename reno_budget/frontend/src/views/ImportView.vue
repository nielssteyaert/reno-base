<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Message from 'primevue/message'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api, apiUrl } from '@/api'
import { useNotify } from '@/composables'
import { day, money, STAGE_OPTIONS, STATUS_LABELS, vatRate } from '@/format'
import { useAppStore } from '@/stores/app'
import type { Stage } from '@/types'

interface Field {
  key: string
  label: string
  required: boolean
  kind: string
}
interface Inspect {
  token: string
  filename: string
  sheets: string[]
  sheet: string | null
  headers: string[]
  sample: string[][]
  row_count: number
  mapping: Record<string, number | null>
}
interface PreviewRow {
  index: number
  values: Record<string, unknown>
  errors: string[]
  warnings: string[]
}
interface Preview {
  rows: PreviewRow[]
  valid_count: number
  error_count: number
  unmatched: { category: string[]; room: string[]; supplier: string[] }
  total_incl_cents: number
}
interface CommitResult {
  created: number
  skipped: number
  payments: number
  created_categories: number
  created_rooms: number
  created_suppliers: number
}
type Kind = 'category' | 'room' | 'supplier'
// Select can't show a null choice, so "create new" is 0 in the UI and null in the API.
const CREATE = 0

const app = useAppStore()
const router = useRouter()
const notify = useNotify()

const step = ref<1 | 2 | 3 | 4>(1)
const fields = ref<Field[]>([])
const inspect = ref<Inspect | null>(null)
const mapping = ref<Record<string, number | null>>({})
const options = reactive({
  amount_includes_vat: true,
  default_vat_rate: null as number | null,
  default_stage: 'invoiced' as Stage,
})
const valueMap = reactive<Record<Kind, Record<string, number>>>({ category: {}, room: {}, supplier: {} })
const preview = ref<Preview | null>(null)
const result = ref<CommitResult | null>(null)
const busy = ref(false)
const dragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const showOnlyProblems = ref(false)

const STEPS = ['Upload', 'Map columns', 'Review', 'Done']

const columnOptions = computed(() =>
  (inspect.value?.headers ?? []).map((header, index) => ({ value: index, label: header || `Column ${index + 1}` })),
)
const missingRequired = computed(() => fields.value.filter((f) => f.required && mapping.value[f.key] == null))
const vatOptions = computed(() => [
  { value: null, label: `Default (${vatRate(app.settings?.default_vat_rate ?? 21)})` },
  ...(app.settings?.vat_rates ?? []).map((r) => ({ value: r, label: vatRate(r) })),
])

const existing = computed<Record<Kind, { value: number; label: string }[]>>(() => ({
  category: [{ value: CREATE, label: '➕ Create new' }, ...app.topCategories.map((c) => ({ value: c.id, label: c.name }))],
  room: [{ value: CREATE, label: '➕ Create new' }, ...app.rooms.map((r) => ({ value: r.id, label: r.name }))],
  supplier: [{ value: CREATE, label: '➕ Create new' }, ...app.suppliers.map((s) => ({ value: s.id, label: s.name }))],
}))
const unmatchedList = computed(() =>
  (['category', 'room', 'supplier'] as Kind[]).flatMap((kind) =>
    Object.keys(valueMap[kind]).map((name) => ({ kind, name })),
  ),
)
const KIND_LABELS: Record<Kind, string> = { category: 'Category', room: 'Room', supplier: 'Supplier' }

const shownRows = computed(() =>
  (preview.value?.rows ?? []).filter((r) => !showOnlyProblems.value || r.errors.length || r.warnings.length),
)

async function upload(files: FileList | null) {
  const file = files?.[0]
  if (!file) return
  busy.value = true
  const form = new FormData()
  form.append('file', file)
  try {
    inspect.value = await api.upload<Inspect>('import/upload', form)
    mapping.value = { ...inspect.value.mapping }
    step.value = 2
  } catch (error) {
    notify.error(error, 'Could not read the file')
  } finally {
    busy.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function changeSheet(sheet: string) {
  if (!inspect.value) return
  try {
    inspect.value = await api.post<Inspect>('import/inspect', { token: inspect.value.token, sheet })
    mapping.value = { ...inspect.value.mapping }
  } catch (error) {
    notify.error(error)
  }
}

function requestBody() {
  const apiMap = Object.fromEntries(
    (Object.keys(valueMap) as Kind[]).map((kind) => [
      kind,
      Object.fromEntries(Object.entries(valueMap[kind]).map(([name, id]) => [name, id === CREATE ? null : id])),
    ]),
  )
  return {
    token: inspect.value!.token,
    sheet: inspect.value!.sheet,
    mapping: mapping.value,
    ...options,
    value_map: apiMap,
  }
}

async function runPreview() {
  busy.value = true
  try {
    preview.value = await api.post<Preview>('import/preview', requestBody())
    // New unmatched names default to "create new"; keep earlier choices.
    for (const kind of ['category', 'room', 'supplier'] as Kind[]) {
      for (const name of preview.value.unmatched[kind]) {
        if (!(name in valueMap[kind])) valueMap[kind][name] = CREATE
      }
    }
    step.value = 3
  } catch (error) {
    notify.error(error, 'Preview failed')
  } finally {
    busy.value = false
  }
}

async function commit() {
  busy.value = true
  try {
    result.value = await api.post<CommitResult>('import/commit', requestBody())
    await Promise.all([app.loadCategories(), app.loadRooms(), app.loadSuppliers()])
    app.touch()
    step.value = 4
  } catch (error) {
    notify.error(error, 'Import failed')
  } finally {
    busy.value = false
  }
}

function restart() {
  inspect.value = null
  preview.value = null
  result.value = null
  for (const kind of ['category', 'room', 'supplier'] as Kind[]) valueMap[kind] = {}
  step.value = 1
}

function cell(values: Record<string, unknown>, key: string) {
  const value = values[key]
  if (value === null || value === undefined || value === '') return '—'
  if (key.endsWith('_date')) return day(String(value))
  return String(value)
}

watch(
  () => [mapping.value, options.amount_includes_vat],
  () => {
    if (step.value === 3) step.value = 2
  },
  { deep: true },
)

onMounted(async () => {
  try {
    fields.value = await api.get<Field[]>('import/fields')
  } catch (error) {
    notify.error(error)
  }
})
</script>

<template>
  <ol class="steps">
    <li v-for="(label, i) in STEPS" :key="label" :class="{ active: step === i + 1, done: step > i + 1 }">
      <span class="dot">{{ step > i + 1 ? '✓' : i + 1 }}</span>{{ label }}
    </li>
  </ol>

  <!-- 1. Upload -->
  <div v-if="step === 1" class="stack">
    <div
      class="card dropzone"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="dragging = false; upload($event.dataTransfer?.files ?? null)"
    >
      <i class="pi pi-file-excel" />
      <h2>Import expenses from Excel or CSV</h2>
      <p class="muted">Drop an .xlsx or .csv file here. Column names in English or Dutch are recognised automatically.</p>
      <div class="row">
        <Button label="Choose file" icon="pi pi-upload" :loading="busy" @click="fileInput?.click()" />
        <a :href="apiUrl('import/template')" download>
          <Button label="Download template" icon="pi pi-download" severity="secondary" outlined />
        </a>
      </div>
      <input ref="fileInput" type="file" accept=".xlsx,.csv" hidden @change="upload(($event.target as HTMLInputElement).files)" />
    </div>
  </div>

  <!-- 2. Map columns -->
  <div v-else-if="step === 2 && inspect" class="stack">
    <div class="card">
      <div class="card-head">
        <h2>{{ inspect.filename }} · {{ inspect.row_count }} rows</h2>
        <Select
          v-if="inspect.sheets.length > 1"
          :model-value="inspect.sheet"
          :options="inspect.sheets"
          aria-label="Sheet"
          @update:model-value="changeSheet"
        />
      </div>
      <div class="mapping">
        <div v-for="field in fields" :key="field.key" class="field">
          <label>{{ field.label }}<span v-if="field.required" class="req"> *</span></label>
          <Select
            v-model="mapping[field.key]"
            :options="columnOptions"
            option-label="label"
            option-value="value"
            show-clear
            placeholder="Not imported"
            :invalid="field.required && mapping[field.key] == null"
          />
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Options</h2>
      <div class="form-grid">
        <div class="field">
          <label>Amounts in the file are</label>
          <div class="row">
            <ToggleSwitch v-model="options.amount_includes_vat" />
            {{ options.amount_includes_vat ? 'including VAT' : 'excluding VAT' }}
          </div>
        </div>
        <div class="field">
          <label>VAT rate when the file has none</label>
          <Select v-model="options.default_vat_rate" :options="vatOptions" option-label="label" option-value="value" />
        </div>
        <div class="field">
          <label>Stage when the file has none</label>
          <Select v-model="options.default_stage" :options="STAGE_OPTIONS" option-label="label" option-value="value" />
        </div>
      </div>
    </div>

    <div class="card" style="overflow-x: auto">
      <h2>First rows of the file</h2>
      <table class="sample">
        <thead>
          <tr><th v-for="(h, i) in inspect.headers" :key="i">{{ h || `Column ${i + 1}` }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(row, r) in inspect.sample" :key="r"><td v-for="(value, c) in row" :key="c">{{ value }}</td></tr>
        </tbody>
      </table>
    </div>

    <div class="row">
      <Button label="Start over" severity="secondary" text icon="pi pi-arrow-left" @click="restart" />
      <span style="flex: 1" />
      <span v-if="missingRequired.length" class="muted small">Map {{ missingRequired.map((f) => f.label).join(' and ') }} to continue.</span>
      <Button label="Preview import" icon="pi pi-arrow-right" icon-pos="right" :disabled="missingRequired.length > 0" :loading="busy" @click="runPreview" />
    </div>
  </div>

  <!-- 3. Review -->
  <div v-else-if="step === 3 && preview" class="stack">
    <div class="kpis">
      <div class="card"><div class="muted small">Rows to import</div><div class="big">{{ preview.valid_count }}</div></div>
      <div class="card"><div class="muted small">Rows with errors (skipped)</div><div class="big" :class="{ bad: preview.error_count }">{{ preview.error_count }}</div></div>
      <div class="card"><div class="muted small">Total incl. VAT</div><div class="big">{{ money(preview.total_incl_cents) }}</div></div>
    </div>

    <div v-if="unmatchedList.length" class="card">
      <h2>New names in the file</h2>
      <p class="muted small" style="margin-top: 0">These don't exist yet. Create them, or map them onto something you already have.</p>
      <div class="mapping">
        <div v-for="item in unmatchedList" :key="`${item.kind}:${item.name}`" class="field">
          <label>{{ KIND_LABELS[item.kind] }}: “{{ item.name }}”</label>
          <Select
            v-model="valueMap[item.kind][item.name]"
            :options="existing[item.kind]"
            option-label="label"
            option-value="value"
            filter
          />
        </div>
      </div>
      <div class="row" style="justify-content: flex-end; margin-top: 12px">
        <Button label="Refresh preview" icon="pi pi-refresh" severity="secondary" outlined size="small" :loading="busy" @click="runPreview" />
      </div>
    </div>

    <div class="card" style="padding: 0; overflow: hidden">
      <div class="card-head" style="padding: 12px 16px 0">
        <h2>Preview</h2>
        <label class="row small"><ToggleSwitch v-model="showOnlyProblems" /> Only rows with problems</label>
      </div>
      <DataTable :value="shownRows" data-key="index" size="small" paginator :rows="25" scrollable>
        <Column header="#" style="width: 50px"><template #body="{ data }">{{ data.index + 1 }}</template></Column>
        <Column header="Title"><template #body="{ data }">{{ cell(data.values, 'title') }}</template></Column>
        <Column header="Category">
          <template #body="{ data }">
            {{ cell(data.values, 'category') }}<template v-if="data.values.subcategory"> › {{ data.values.subcategory }}</template>
          </template>
        </Column>
        <Column header="Room"><template #body="{ data }">{{ cell(data.values, 'room') }}</template></Column>
        <Column header="Supplier"><template #body="{ data }">{{ cell(data.values, 'supplier') }}</template></Column>
        <Column header="Stage">
          <template #body="{ data }">{{ STATUS_LABELS[data.values.stage as Stage] ?? cell(data.values, 'stage') }}</template>
        </Column>
        <Column header="Date"><template #body="{ data }">{{ cell(data.values, 'expense_date') }}</template></Column>
        <Column header="Incl. VAT" class="num">
          <template #body="{ data }">{{ data.values.amount_incl_cents != null ? money(data.values.amount_incl_cents as number) : '—' }}</template>
        </Column>
        <Column header="Paid" class="num">
          <template #body="{ data }">{{ data.values.paid_cents ? money(data.values.paid_cents as number) : '—' }}</template>
        </Column>
        <Column header="Problems" style="min-width: 220px">
          <template #body="{ data }">
            <div v-for="e in data.errors" :key="e" class="problem error"><i class="pi pi-times-circle" /> {{ e }}</div>
            <div v-for="w in data.warnings" :key="w" class="problem warning"><i class="pi pi-exclamation-triangle" /> {{ w }}</div>
          </template>
        </Column>
      </DataTable>
    </div>

    <div class="row">
      <Button label="Back to mapping" severity="secondary" text icon="pi pi-arrow-left" @click="step = 2" />
      <span style="flex: 1" />
      <Button
        :label="`Import ${preview.valid_count} expense(s)`"
        icon="pi pi-check"
        :disabled="!preview.valid_count"
        :loading="busy"
        @click="commit"
      />
    </div>
  </div>

  <!-- 4. Done -->
  <div v-else-if="step === 4 && result" class="card done">
    <i class="pi pi-check-circle" />
    <h2>Imported {{ result.created }} expense(s)</h2>
    <p class="muted">
      {{ result.payments }} payment(s) recorded · {{ result.created_categories }} new categories ·
      {{ result.created_rooms }} new rooms · {{ result.created_suppliers }} new suppliers
      <template v-if="result.skipped"> · {{ result.skipped }} row(s) skipped</template>
    </p>
    <div class="row" style="justify-content: center">
      <Button label="View expenses" icon="pi pi-receipt" @click="router.push('/expenses')" />
      <Button label="Import another file" severity="secondary" outlined @click="restart" />
    </div>
  </div>

  <Message v-else severity="warn">Something went wrong. <a href="#" @click.prevent="restart">Start again</a>.</Message>
</template>

<style scoped>
.steps {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  padding: 0;
  margin: 0 0 18px;
}
.steps li {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
}
.steps li.active {
  color: var(--text);
  font-weight: 600;
}
.steps .dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 12px;
  background: var(--surface-sunken);
  border: 1px solid var(--border);
}
.steps li.active .dot,
.steps li.done .dot {
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  border-color: transparent;
}
.dropzone {
  text-align: center;
  padding: 48px 24px;
  border-style: dashed;
  border-width: 2px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.dropzone.dragging {
  border-color: var(--p-primary-color);
  background: var(--nav-active);
}
.dropzone > .pi {
  font-size: 36px;
  color: var(--p-primary-color);
  margin-bottom: 8px;
}
.mapping {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px 16px;
}
.req {
  color: var(--status-critical-text);
}
.sample {
  border-collapse: collapse;
  font-size: 12px;
  width: 100%;
}
.sample th,
.sample td {
  border: 1px solid var(--border);
  padding: 4px 8px;
  text-align: left;
  white-space: nowrap;
}
.sample th {
  background: var(--surface-sunken);
}
.big {
  font-size: 22px;
  font-weight: 650;
}
.big.bad {
  color: var(--status-critical-text);
}
.problem {
  font-size: 12px;
}
.problem.error {
  color: var(--status-critical-text);
}
.problem.warning {
  color: var(--status-warning-text);
}
.done {
  text-align: center;
  padding: 40px;
}
.done > .pi {
  font-size: 40px;
  color: var(--status-good);
}
</style>
