<script setup lang="ts">
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import Textarea from 'primevue/textarea'
import { computed, reactive, ref, watch } from 'vue'
import { api } from '@/api'
import { useConfirmDelete, useNotify } from '@/composables'
import { money, STAGE_OPTIONS, vatRate } from '@/format'
import { useAppStore } from '@/stores/app'
import { useDrawerStore } from '@/stores/drawer'
import type { AuditEntry, ExpenseDetail, Stage } from '@/types'
import AttachmentsPanel from './AttachmentsPanel.vue'
import DateInput from './DateInput.vue'
import HistoryList from './HistoryList.vue'
import MoneyInput from './MoneyInput.vue'
import PaymentsPanel from './PaymentsPanel.vue'
import QuickCreate from './QuickCreate.vue'
import StatusTag from './StatusTag.vue'

const app = useAppStore()
const drawer = useDrawerStore()
const notify = useNotify()
const confirmDelete = useConfirmDelete()

const detail = ref<ExpenseDetail | null>(null)
const tab = ref('details')
const saving = ref(false)
const loading = ref(false)
const history = ref<AuditEntry[]>([])
const submitted = ref(false)

const emptyForm = () => ({
  title: '',
  stage: 'estimate' as Stage,
  category_id: null as number | null,
  room_id: null as number | null,
  supplier_id: null as number | null,
  milestone_id: null as number | null,
  vat_rate: app.settings?.default_vat_rate ?? 21,
  expense_date: null as string | null,
  due_date: null as string | null,
  quote_ref: null as string | null,
  invoice_no: null as string | null,
  description: null as string | null,
  notes: null as string | null,
})

const form = reactive(emptyForm())
const amount = ref<number | null>(null)
const amountMode = ref<'excl' | 'incl'>('excl')
const amountDirty = ref(false)
const originalRate = ref<number | null>(null)

const isNew = computed(() => detail.value === null)
const header = computed(() => (isNew.value ? 'New expense' : detail.value?.title || 'Expense'))

const vatOptions = computed(() =>
  (app.settings?.vat_rates ?? [0, 6, 21]).map((rate) => ({ value: rate, label: vatRate(rate) })),
)
const amountModes = [
  { value: 'excl', label: 'Excl. VAT' },
  { value: 'incl', label: 'Incl. VAT' },
]
const roomOptions = computed(() => app.rooms.filter((r) => !r.archived || r.id === form.room_id))
const supplierOptions = computed(() =>
  app.suppliers.filter((s) => !s.archived || s.id === form.supplier_id),
)

const preview = computed(() => {
  const value = amount.value ?? 0
  const rate = form.vat_rate ?? 0
  if (amountMode.value === 'excl') {
    const vat = Math.round((value * rate) / 100)
    return { excl: value, vat, incl: value + vat }
  }
  const excl = Math.round((value * 100) / (100 + rate))
  return { excl, vat: value - excl, incl: value }
})

function fill(source: Partial<ExpenseDetail>) {
  Object.assign(form, emptyForm())
  for (const key of Object.keys(form) as (keyof typeof form)[]) {
    if (source[key] !== undefined) (form as Record<string, unknown>)[key] = source[key]
  }
  amount.value = source.amount_excl_cents ?? null
  amountMode.value = 'excl'
  amountDirty.value = false
  originalRate.value = source.vat_rate ?? null
  submitted.value = false
}

async function load() {
  tab.value = 'details'
  history.value = []
  if (drawer.expenseId === null) {
    detail.value = null
    fill(drawer.defaults)
    return
  }
  loading.value = true
  try {
    detail.value = await api.get<ExpenseDetail>(`expenses/${drawer.expenseId}`)
    fill(detail.value)
  } catch (error) {
    notify.error(error, 'Could not load expense')
    drawer.close()
  } finally {
    loading.value = false
  }
}

watch(
  () => [drawer.visible, drawer.expenseId] as const,
  ([visible]) => {
    if (visible) load()
  },
)

watch(tab, async (value) => {
  if (value === 'history' && detail.value) {
    const page = await api.get<{ items: AuditEntry[] }>('audit', { expense_id: detail.value.id, limit: 200 })
    history.value = page.items
  }
})

function switchMode(mode: 'excl' | 'incl') {
  if (mode === amountMode.value || amount.value === null) {
    amountMode.value = mode
    return
  }
  amount.value = mode === 'incl' ? preview.value.incl : preview.value.excl
  amountMode.value = mode
}

async function save() {
  submitted.value = true
  if (!form.title.trim()) return
  saving.value = true
  const creating = isNew.value
  try {
    const body: Record<string, unknown> = { ...form, title: form.title.trim() }
    if (creating || amountDirty.value) {
      body.amount_cents = amount.value ?? 0
      body.amount_includes_vat = amountMode.value === 'incl'
    } else if (form.vat_rate === originalRate.value) {
      delete body.vat_rate
    }
    const saved = creating
      ? await api.post<ExpenseDetail>('expenses', body)
      : await api.patch<ExpenseDetail>(`expenses/${detail.value!.id}`, body)
    detail.value = saved
    drawer.expenseId = saved.id
    fill(saved)
    app.touch()
    notify.success(creating ? 'Expense created' : 'Expense saved')
  } catch (error) {
    notify.error(error, 'Could not save expense')
  } finally {
    saving.value = false
  }
}

async function duplicate() {
  if (!detail.value) return
  try {
    const copy = await api.post<ExpenseDetail>(`expenses/${detail.value.id}/duplicate`)
    app.touch()
    drawer.open(copy.id)
    notify.success('Expense duplicated')
  } catch (error) {
    notify.error(error, 'Could not duplicate')
  }
}

function remove() {
  if (!detail.value) return
  const expense = detail.value
  confirmDelete(
    `Delete “${expense.title}” with its ${expense.payment_count} payment(s) and ${expense.attachment_count} attachment(s)?`,
    async () => {
      try {
        await api.del(`expenses/${expense.id}`)
        app.touch()
        drawer.close()
        notify.success('Expense deleted')
      } catch (error) {
        notify.error(error, 'Could not delete')
      }
    },
  )
}

async function refreshDetail() {
  if (!detail.value) return
  detail.value = await api.get<ExpenseDetail>(`expenses/${detail.value.id}`)
  app.touch()
}

async function quickCreate(kind: 'suppliers' | 'rooms', name: string) {
  try {
    const created = await api.post<{ id: number }>(kind, { name })
    if (kind === 'suppliers') {
      await app.loadSuppliers()
      form.supplier_id = created.id
    } else {
      await app.loadRooms()
      form.room_id = created.id
    }
  } catch (error) {
    notify.error(error)
  }
}
</script>

<template>
  <Drawer
    v-model:visible="drawer.visible"
    position="right"
    class="expense-drawer"
    :block-scroll="true"
  >
    <template #header>
      <div class="drawer-head">
        <span class="drawer-title">{{ header }}</span>
        <StatusTag v-if="detail" :status="detail.status" />
      </div>
    </template>

    <div v-if="loading" class="empty">Loading…</div>
    <Tabs v-else v-model:value="tab">
      <TabList>
        <Tab value="details">Details</Tab>
        <Tab value="payments" :disabled="isNew">
          Payments<span v-if="detail?.payment_count" class="count">{{ detail.payment_count }}</span>
        </Tab>
        <Tab value="attachments" :disabled="isNew">
          Files<span v-if="detail?.attachment_count" class="count">{{ detail.attachment_count }}</span>
        </Tab>
        <Tab value="history" :disabled="isNew">History</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="details">
          <form class="form-grid" @submit.prevent="save">
            <div class="field full">
              <label for="exp-title">Title</label>
              <InputText
                id="exp-title"
                v-model="form.title"
                :invalid="submitted && !form.title.trim()"
                placeholder="e.g. Kitchen cabinets"
                autofocus
              />
            </div>

            <div class="field full">
              <label>Stage</label>
              <SelectButton
                v-model="form.stage"
                :options="STAGE_OPTIONS"
                option-label="label"
                option-value="value"
                :allow-empty="false"
              />
              <span class="hint">“Paid” is set automatically once payments cover the total.</span>
            </div>

            <div class="field full">
              <label for="exp-amount">Amount</label>
              <div class="amount-row">
                <MoneyInput
                  v-model="amount"
                  input-id="exp-amount"
                  @update:model-value="amountDirty = true"
                />
                <SelectButton
                  :model-value="amountMode"
                  :options="amountModes"
                  option-label="label"
                  option-value="value"
                  :allow-empty="false"
                  @update:model-value="switchMode"
                />
                <Select
                  v-model="form.vat_rate"
                  :options="vatOptions"
                  option-label="label"
                  option-value="value"
                  aria-label="VAT rate"
                  class="vat-select"
                />
              </div>
              <span class="hint">
                Excl. {{ money(preview.excl) }} · VAT {{ money(preview.vat) }} ·
                <strong>Incl. {{ money(preview.incl) }}</strong>
              </span>
            </div>

            <div class="field">
              <label for="exp-category">Category</label>
              <Select
                v-model="form.category_id"
                input-id="exp-category"
                :options="app.categoryOptions(form.category_id)"
                option-label="label"
                option-value="value"
                filter
                show-clear
                placeholder="Choose a category"
              />
            </div>
            <div class="field">
              <label for="exp-room">Room</label>
              <div class="row">
                <Select
                  v-model="form.room_id"
                  input-id="exp-room"
                  :options="roomOptions"
                  option-label="name"
                  option-value="id"
                  filter
                  show-clear
                  placeholder="Choose a room"
                  class="grow"
                />
                <QuickCreate label="room" @create="quickCreate('rooms', $event)" />
              </div>
            </div>
            <div class="field">
              <label for="exp-supplier">Supplier</label>
              <div class="row">
                <Select
                  v-model="form.supplier_id"
                  input-id="exp-supplier"
                  :options="supplierOptions"
                  option-label="name"
                  option-value="id"
                  filter
                  show-clear
                  placeholder="Choose a supplier"
                  class="grow"
                />
                <QuickCreate label="supplier" @create="quickCreate('suppliers', $event)" />
              </div>
            </div>
            <div class="field">
              <label for="exp-milestone">Milestone</label>
              <Select
                v-model="form.milestone_id"
                input-id="exp-milestone"
                :options="app.milestones"
                option-label="name"
                option-value="id"
                show-clear
                placeholder="None"
              />
            </div>

            <div class="field">
              <label for="exp-date">Date</label>
              <DateInput v-model="form.expense_date" input-id="exp-date" />
            </div>
            <div class="field">
              <label for="exp-due">Due date</label>
              <DateInput v-model="form.due_date" input-id="exp-due" />
            </div>
            <div class="field">
              <label for="exp-quote">Quote reference</label>
              <InputText id="exp-quote" v-model="form.quote_ref" />
            </div>
            <div class="field">
              <label for="exp-invoice">Invoice number</label>
              <InputText id="exp-invoice" v-model="form.invoice_no" />
            </div>
            <div class="field full">
              <label for="exp-description">Description</label>
              <Textarea id="exp-description" v-model="form.description" rows="2" auto-resize />
            </div>
            <div class="field full">
              <label for="exp-notes">Notes</label>
              <Textarea id="exp-notes" v-model="form.notes" rows="2" auto-resize />
            </div>

            <Message v-if="detail && detail.paid_cents > detail.amount_incl_cents" severity="warn" class="full">
              Payments ({{ money(detail.paid_cents) }}) exceed the total incl. VAT.
            </Message>

            <div class="actions full">
              <Button
                v-if="!isNew"
                label="Delete"
                icon="pi pi-trash"
                severity="danger"
                text
                @click="remove"
              />
              <Button v-if="!isNew" label="Duplicate" icon="pi pi-copy" severity="secondary" text @click="duplicate" />
              <span class="grow" />
              <Button label="Close" severity="secondary" outlined @click="drawer.close()" />
              <Button type="submit" :label="isNew ? 'Create' : 'Save'" icon="pi pi-check" :loading="saving" />
            </div>
          </form>
        </TabPanel>
        <TabPanel value="payments">
          <PaymentsPanel v-if="detail" :expense="detail" @changed="refreshDetail" />
        </TabPanel>
        <TabPanel value="attachments">
          <AttachmentsPanel v-if="detail" :expense="detail" @changed="refreshDetail" />
        </TabPanel>
        <TabPanel value="history">
          <HistoryList :entries="history" :show-entity="true" />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </Drawer>
</template>

<style scoped>
.drawer-head {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.drawer-title {
  font-weight: 650;
  font-size: 17px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.count {
  margin-left: 6px;
  font-size: 11px;
  background: var(--surface-sunken);
  border-radius: 10px;
  padding: 1px 7px;
}
.amount-row {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) auto 100px;
  gap: 8px;
}
@media (max-width: 640px) {
  .amount-row {
    grid-template-columns: 1fr;
  }
}
.actions {
  display: flex;
  gap: 8px;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}
.grow {
  flex: 1;
  min-width: 0;
}
</style>
