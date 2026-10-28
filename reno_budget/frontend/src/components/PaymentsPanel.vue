<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import ProgressBar from 'primevue/progressbar'
import Select from 'primevue/select'
import { computed, reactive, watch } from 'vue'
import { api } from '@/api'
import { useConfirmDelete, useNotify } from '@/composables'
import { day, METHOD_LABELS, METHOD_OPTIONS, money, PAYMENT_STATUS_LABELS, todayIso } from '@/format'
import type { ExpenseDetail, Payment, PaymentMethod } from '@/types'
import DateInput from './DateInput.vue'
import MoneyInput from './MoneyInput.vue'

const props = defineProps<{ expense: ExpenseDetail }>()
const emit = defineEmits<{ changed: [] }>()
const notify = useNotify()
const confirmDelete = useConfirmDelete()

const remaining = computed(() => Math.max(props.expense.amount_incl_cents - props.expense.paid_cents, 0))
const progress = computed(() =>
  props.expense.amount_incl_cents
    ? Math.min(100, Math.round((props.expense.paid_cents / props.expense.amount_incl_cents) * 100))
    : 0,
)

const form = reactive({
  date: todayIso() as string | null,
  amount_cents: null as number | null,
  method: 'bank_transfer' as PaymentMethod,
  reference: '',
})

function resetForm() {
  form.date = todayIso()
  form.amount_cents = remaining.value || null
  form.reference = ''
}

watch(() => props.expense.id, resetForm, { immediate: true })

async function add() {
  if (!form.date || !form.amount_cents) return
  try {
    await api.post(`expenses/${props.expense.id}/payments`, {
      date: form.date,
      amount_cents: form.amount_cents,
      method: form.method,
      reference: form.reference || null,
    })
    notify.success('Payment added')
    emit('changed')
  } catch (error) {
    notify.error(error, 'Could not add payment')
  }
}

async function payRemaining() {
  try {
    await api.post(`expenses/${props.expense.id}/pay-remaining`, {
      date: form.date ?? todayIso(),
      method: form.method,
      reference: form.reference || null,
    })
    notify.success('Marked as fully paid')
    emit('changed')
  } catch (error) {
    notify.error(error, 'Could not record payment')
  }
}

function remove(payment: Payment) {
  confirmDelete(`Delete the payment of ${money(payment.amount_cents)} on ${day(payment.date)}?`, async () => {
    try {
      await api.del(`payments/${payment.id}`)
      emit('changed')
    } catch (error) {
      notify.error(error)
    }
  })
}

watch(
  () => props.expense.paid_cents,
  () => resetForm(),
)
</script>

<template>
  <div class="stack">
    <div class="summary card">
      <div>
        <div class="muted small">Total incl. VAT</div>
        <div class="big">{{ money(props.expense.amount_incl_cents) }}</div>
      </div>
      <div>
        <div class="muted small">Paid</div>
        <div class="big">{{ money(props.expense.paid_cents) }}</div>
      </div>
      <div>
        <div class="muted small">Still to pay</div>
        <div class="big">{{ money(remaining) }}</div>
      </div>
      <div class="full">
        <ProgressBar :value="progress" :show-value="false" style="height: 8px" />
        <div class="muted small" style="margin-top: 6px">
          {{ PAYMENT_STATUS_LABELS[props.expense.payment_status] }} · {{ progress }}%
        </div>
      </div>
    </div>

    <DataTable :value="props.expense.payments" size="small" data-key="id">
      <template #empty><span class="muted">No payments yet.</span></template>
      <Column header="Date"><template #body="{ data }">{{ day(data.date) }}</template></Column>
      <Column header="Amount" class="num"><template #body="{ data }">{{ money(data.amount_cents) }}</template></Column>
      <Column header="Method"><template #body="{ data }">{{ METHOD_LABELS[data.method as PaymentMethod] }}</template></Column>
      <Column field="reference" header="Reference" />
      <Column style="width: 48px">
        <template #body="{ data }">
          <Button icon="pi pi-trash" text rounded severity="danger" aria-label="Delete payment" @click="remove(data)" />
        </template>
      </Column>
    </DataTable>

    <form class="card add-form" @submit.prevent="add">
      <h2>Add a payment</h2>
      <div class="form-grid">
        <div class="field">
          <label>Date</label>
          <DateInput v-model="form.date" />
        </div>
        <div class="field">
          <label>Amount (incl. VAT)</label>
          <MoneyInput v-model="form.amount_cents" />
        </div>
        <div class="field">
          <label>Method</label>
          <Select v-model="form.method" :options="METHOD_OPTIONS" option-label="label" option-value="value" />
        </div>
        <div class="field">
          <label>Reference</label>
          <InputText v-model="form.reference" placeholder="e.g. deposit 30%" />
        </div>
      </div>
      <div class="row" style="margin-top: 12px; justify-content: flex-end">
        <Button
          v-if="remaining > 0"
          type="button"
          label="Pay remaining"
          icon="pi pi-check-circle"
          severity="secondary"
          outlined
          @click="payRemaining"
        />
        <Button type="submit" label="Add payment" icon="pi pi-plus" :disabled="!form.date || !form.amount_cents" />
      </div>
    </form>
  </div>
</template>

<style scoped>
.summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.summary .full {
  grid-column: 1 / -1;
}
.big {
  font-size: 18px;
  font-weight: 650;
}
</style>
