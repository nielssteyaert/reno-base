<script setup lang="ts">
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import { computed, reactive, ref, watch } from 'vue'
import { api } from '@/api'
import DateInput from '@/components/DateInput.vue'
import MoneyInput from '@/components/MoneyInput.vue'
import { useNotify } from '@/composables'
import { money, vatRate } from '@/format'
import { useAppStore } from '@/stores/app'
import type { Settings } from '@/types'

const app = useAppStore()
const notify = useNotify()
const saving = ref(false)
const newRate = ref<number | null>(null)

const form = reactive<Settings>({ ...(app.settings as Settings) })
watch(
  () => app.settings,
  (value) => value && Object.assign(form, value, { vat_rates: [...value.vat_rates] }),
  { immediate: true },
)

const currencies = ['EUR', 'USD', 'GBP', 'CHF', 'SEK', 'NOK', 'DKK', 'PLN', 'CZK']
const locales = [
  { value: 'nl-BE', label: 'Dutch (Belgium): € 1.234,56' },
  { value: 'fr-BE', label: 'French (Belgium): 1 234,56 €' },
  { value: 'nl-NL', label: 'Dutch (Netherlands): € 1.234,56' },
  { value: 'de-DE', label: 'German: 1.234,56 €' },
  { value: 'en-IE', label: 'English (Ireland): €1,234.56' },
  { value: 'en-GB', label: 'English (UK): €1,234.56' },
  { value: 'en-US', label: 'English (US): €1,234.56' },
]

const reserve = computed(() => Math.round((form.total_budget_cents * form.contingency_pct) / 100))

function addRate() {
  if (newRate.value === null || form.vat_rates.includes(newRate.value)) return
  form.vat_rates = [...form.vat_rates, newRate.value].sort((a, b) => a - b)
  newRate.value = null
}

function removeRate(rate: number) {
  if (rate === form.default_vat_rate) return
  form.vat_rates = form.vat_rates.filter((r) => r !== rate)
}

async function save() {
  saving.value = true
  try {
    await api.patch('settings', form)
    await app.loadSettings()
    app.touch()
    notify.success('Settings saved')
  } catch (error) {
    notify.error(error, 'Could not save settings')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="stack settings" @submit.prevent="save">
    <div class="card">
      <h2>Project</h2>
      <div class="form-grid">
        <div class="field full">
          <label for="set-name">Project name</label>
          <InputText id="set-name" v-model="form.project_name" />
        </div>
        <div class="field">
          <label>Start date</label>
          <DateInput v-model="form.start_date" />
        </div>
        <div class="field">
          <label>Target completion</label>
          <DateInput v-model="form.target_end_date" />
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Budget</h2>
      <div class="form-grid">
        <div class="field">
          <label for="set-budget">Total budget (incl. VAT)</label>
          <MoneyInput v-model="form.total_budget_cents" input-id="set-budget" />
          <span class="hint">Everything you can spend, including the contingency reserve.</span>
        </div>
        <div class="field">
          <label for="set-contingency">Contingency reserve</label>
          <InputNumber
            v-model="form.contingency_pct"
            input-id="set-contingency"
            suffix=" %"
            :min="0"
            :max="100"
            :max-fraction-digits="1"
            fluid
          />
          <span class="hint">
            {{ money(reserve) }} kept aside for surprises; working budget {{ money(form.total_budget_cents - reserve) }}.
          </span>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>VAT</h2>
      <div class="form-grid">
        <div class="field">
          <label>VAT rates</label>
          <div class="row wrap">
            <Chip
              v-for="rate in form.vat_rates"
              :key="rate"
              :label="vatRate(rate)"
              :removable="rate !== form.default_vat_rate"
              @remove="removeRate(rate)"
            />
          </div>
          <div class="row">
            <InputNumber v-model="newRate" suffix=" %" :min="0" :max="100" :max-fraction-digits="2" placeholder="Add rate" />
            <Button type="button" icon="pi pi-plus" severity="secondary" outlined aria-label="Add rate" @click="addRate" />
          </div>
          <span class="hint">In Belgium: 6% for renovating homes older than 10 years, otherwise 21%.</span>
        </div>
        <div class="field">
          <label for="set-default-vat">Default rate for new expenses</label>
          <Select
            v-model="form.default_vat_rate"
            input-id="set-default-vat"
            :options="form.vat_rates.map((r) => ({ value: r, label: vatRate(r) }))"
            option-label="label"
            option-value="value"
          />
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Display</h2>
      <div class="form-grid">
        <div class="field">
          <label for="set-currency">Currency</label>
          <Select v-model="form.currency" input-id="set-currency" :options="currencies" />
        </div>
        <div class="field">
          <label for="set-locale">Number and date format</label>
          <Select v-model="form.locale" input-id="set-locale" :options="locales" option-label="label" option-value="value" />
        </div>
      </div>
    </div>

    <div class="row" style="justify-content: flex-end">
      <Button type="submit" label="Save settings" icon="pi pi-check" :loading="saving" />
    </div>

    <p class="muted small">
      Signed in as {{ app.user }}. Backup schedule and log level are set on the app's Configuration tab in
      Home Assistant.
    </p>
  </form>
</template>

<style scoped>
.settings {
  max-width: 860px;
}
.wrap {
  flex-wrap: wrap;
}
</style>
