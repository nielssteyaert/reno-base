<script setup lang="ts">
import Button from 'primevue/button'
import Chart from 'primevue/chart'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import SelectButton from 'primevue/selectbutton'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import Tabs from 'primevue/tabs'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, download } from '@/api'
import BudgetBar from '@/components/BudgetBar.vue'
import BudgetLegend from '@/components/BudgetLegend.vue'
import BudgetTable from '@/components/BudgetTable.vue'
import KpiTile from '@/components/KpiTile.vue'
import ReportFilters from '@/components/ReportFilters.vue'
import SpendingCharts from '@/components/SpendingCharts.vue'
import { useChartTheme } from '@/components/useChartTheme'
import { useNotify } from '@/composables'
import { day, money, moneyCompact, monthLabel, pct } from '@/format'
import { useAppStore } from '@/stores/app'
import type { MonthRow, NamedLine, ReportFilters as Filters, Summary } from '@/types'

const app = useAppStore()
const route = useRoute()
const router = useRouter()
const notify = useNotify()
const theme = useChartTheme()

const TABS = ['budget', 'spending', 'forecast', 'suppliers'] as const
type TabKey = (typeof TABS)[number]
const tab = computed<TabKey>({
  get: () => (TABS.includes(route.params.tab as TabKey) ? (route.params.tab as TabKey) : 'budget'),
  set: (value) => router.replace({ name: 'reports', params: { tab: value } }),
})

const filters = ref<Filters>({})
const loading = ref(false)

// Budget vs actual
const dimension = ref<'categories' | 'rooms'>('categories')
const budgetRows = ref<NamedLine[]>([])
// Spending over time
const months = ref<MonthRow[]>([])
const monthlyBudget = ref(0)
const showMonthTable = ref(false)
// Forecast
const forecast = ref<{ summary: Summary; categories: NamedLine[]; upcoming: { month: string; amount: number }[] } | null>(null)
// Suppliers
const supplierRows = ref<NamedLine[]>([])

async function load() {
  loading.value = true
  const query = { ...filters.value }
  try {
    if (tab.value === 'budget') {
      budgetRows.value = await api.get<NamedLine[]>(`reports/${dimension.value}`, query)
    } else if (tab.value === 'spending') {
      const data = await api.get<{ budget: number; months: MonthRow[] }>('reports/monthly', query)
      months.value = data.months
      monthlyBudget.value = data.budget
    } else if (tab.value === 'forecast') {
      forecast.value = await api.get('reports/forecast', query)
    } else {
      supplierRows.value = await api.get<NamedLine[]>('reports/suppliers', query)
    }
  } catch (error) {
    notify.error(error, 'Could not load report')
  } finally {
    loading.value = false
  }
}

async function exportReport() {
  const name = tab.value === 'budget' ? dimension.value : tab.value === 'spending' ? 'monthly' : tab.value
  try {
    await download(`export/report/${name}`, { query: { ...filters.value }, fallback: `${name}.xlsx` })
  } catch (error) {
    notify.error(error, 'Export failed')
  }
}

async function exportWorkbook() {
  try {
    await download('export/workbook', { query: { ...filters.value }, fallback: 'renovation-budget.xlsx' })
  } catch (error) {
    notify.error(error, 'Export failed')
  }
}

function drill(row: NamedLine, kind: 'category' | 'room' | 'supplier') {
  if (row.id === null) return
  router.push({ path: '/expenses', query: { [kind]: row.id } })
}

const supplierScale = computed(() => Math.max(1, ...supplierRows.value.map((s) => s.forecast)))

const f = computed(() => forecast.value?.summary)
const forecastTone = computed(() => {
  if (!f.value?.budget) return undefined
  return f.value.over_budget ? 'critical' : f.value.uses_contingency ? 'warning' : 'good'
})

const upcomingChart = computed(() => {
  const rows = forecast.value?.upcoming ?? []
  const c = theme.value
  return {
    data: {
      labels: rows.map((r) => (r.month === 'unscheduled' ? 'No due date' : monthLabel(r.month))),
      datasets: [
        {
          label: 'To pay',
          data: rows.map((r) => r.amount),
          backgroundColor: c.series1,
          borderRadius: 4,
          borderSkipped: 'start',
          maxBarThickness: 32,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx: { parsed: { y: number | null } }) => money(ctx.parsed.y ?? 0) } },
      },
      scales: {
        x: { grid: { display: false }, border: { color: c.baseline }, ticks: { color: c.muted } },
        y: {
          beginAtZero: true,
          grid: { color: c.grid },
          border: { display: false },
          ticks: { color: c.muted, callback: (v: number | string) => moneyCompact(Number(v)) },
        },
      },
    },
  }
})

watch([tab, dimension, filters], load, { deep: true })
watch(() => app.dataVersion, load)
onMounted(load)
</script>

<template>
  <Tabs :value="tab" @update:value="tab = $event as TabKey">
    <TabList>
      <Tab value="budget"><i class="pi pi-chart-bar" /> Budget vs actual</Tab>
      <Tab value="spending"><i class="pi pi-chart-line" /> Spending over time</Tab>
      <Tab value="forecast"><i class="pi pi-compass" /> Forecast</Tab>
      <Tab value="suppliers"><i class="pi pi-users" /> Suppliers</Tab>
    </TabList>
  </Tabs>

  <div style="margin-top: 16px">
    <ReportFilters v-model="filters">
      <span class="spacer" />
      <Button label="Export report" icon="pi pi-file-excel" severity="secondary" outlined @click="exportReport" />
      <Button v-tooltip.bottom="'All sheets: summary, expenses, payments, categories, rooms, suppliers, milestones, monthly'" label="Full workbook" icon="pi pi-download" @click="exportWorkbook" />
    </ReportFilters>
  </div>
  <p class="muted small" style="margin: -6px 0 14px">All amounts incl. VAT. Filters apply to expenses; budgets are not filtered.</p>

  <!-- Budget vs actual -->
  <div v-if="tab === 'budget'" class="card">
    <div class="card-head">
      <SelectButton
        v-model="dimension"
        :options="[
          { value: 'categories', label: 'By category' },
          { value: 'rooms', label: 'By room' },
        ]"
        option-label="label"
        option-value="value"
        :allow-empty="false"
      />
      <BudgetLegend />
    </div>
    <BudgetTable
      :rows="budgetRows"
      :name-header="dimension === 'categories' ? 'Category' : 'Room'"
      @select="drill($event, dimension === 'categories' ? 'category' : 'room')"
    />
  </div>

  <!-- Spending over time -->
  <div v-else-if="tab === 'spending'" class="stack">
    <div v-if="!months.length && !loading" class="card empty"><i class="pi pi-chart-line" />No payments or committed expenses yet.</div>
    <template v-else>
      <SpendingCharts :months="months" :budget="monthlyBudget" />
      <div class="card">
        <div class="card-head">
          <h2>Data table</h2>
          <Button :label="showMonthTable ? 'Hide' : 'Show'" text size="small" @click="showMonthTable = !showMonthTable" />
        </div>
        <DataTable v-if="showMonthTable" :value="months" size="small" data-key="month">
          <Column header="Month"><template #body="{ data }">{{ monthLabel(data.month) }}</template></Column>
          <Column header="Paid" class="num"><template #body="{ data }">{{ money(data.paid) }}</template></Column>
          <Column header="Committed" class="num"><template #body="{ data }">{{ money(data.committed) }}</template></Column>
          <Column header="Paid (cumulative)" class="num"><template #body="{ data }">{{ money(data.cumulative_paid) }}</template></Column>
          <Column header="Committed (cumulative)" class="num"><template #body="{ data }">{{ money(data.cumulative_committed) }}</template></Column>
        </DataTable>
      </div>
    </template>
  </div>

  <!-- Forecast -->
  <div v-else-if="tab === 'forecast' && f" class="stack">
    <div class="kpis">
      <KpiTile label="Paid" :value="money(f.paid)" icon="pi pi-credit-card" />
      <KpiTile label="Committed, unpaid" :value="money(f.outstanding)" icon="pi pi-file-check" />
      <KpiTile label="Open quotes" :value="money(f.quoted)" icon="pi pi-file" />
      <KpiTile label="Estimates" :value="money(f.estimated)" icon="pi pi-pencil" />
      <KpiTile
        label="Projected final cost"
        :value="money(f.forecast)"
        icon="pi pi-compass"
        :tone="forecastTone"
        :sub="
          !f.budget
            ? 'No budget set'
            : f.over_budget
              ? `${money(f.forecast - f.budget)} over budget`
              : f.uses_contingency
                ? `Uses ${money(f.contingency_used)} of contingency`
                : `${money(f.working_budget - f.forecast)} left in working budget`
        "
      />
    </div>
    <div class="card">
      <div class="card-head">
        <h2>Projected cost vs budget</h2>
        <BudgetLegend />
      </div>
      <BudgetBar
        :paid="f.paid"
        :outstanding="f.outstanding"
        :quoted="f.quoted"
        :estimated="f.estimated"
        :budget="f.budget"
        :reference="f.budget && f.contingency_reserve ? f.working_budget : null"
        :height="24"
      />
      <p class="muted small">
        Projected final cost = paid + committed but unpaid + open quotes + estimates.
        Budget {{ money(f.budget) }} includes a contingency reserve of {{ money(f.contingency_reserve) }}
        ({{ f.contingency_pct }}%); the dashed line is the working budget ({{ money(f.working_budget) }}).
        <template v-if="f.budget">Forecast is {{ pct(f.pct_forecast) }} of the total budget.</template>
      </p>
    </div>
    <div class="grid grid-2">
      <div class="card">
        <h2>Forecast by category</h2>
        <BudgetTable :rows="forecast!.categories" compact name-header="Category" @select="drill($event, 'category')" />
      </div>
      <div class="card">
        <h2>Upcoming payments</h2>
        <div v-if="!forecast!.upcoming.length" class="empty small">Nothing left to pay on committed expenses.</div>
        <template v-else>
          <div style="height: 240px; position: relative">
            <Chart type="bar" :data="upcomingChart.data" :options="upcomingChart.options" style="height: 100%" />
          </div>
          <DataTable :value="forecast!.upcoming" size="small" data-key="month" style="margin-top: 12px">
            <Column header="Due">
              <template #body="{ data }">{{ data.month === 'unscheduled' ? 'No due date' : monthLabel(data.month) }}</template>
            </Column>
            <Column header="Amount" class="num"><template #body="{ data }">{{ money(data.amount) }}</template></Column>
          </DataTable>
        </template>
      </div>
    </div>
  </div>

  <!-- Suppliers -->
  <div v-else-if="tab === 'suppliers'" class="card">
    <div class="card-head">
      <h2>Spend per supplier</h2>
      <BudgetLegend />
    </div>
    <DataTable
      :value="supplierRows"
      size="small"
      :data-key="(row: NamedLine) => String(row.id)"
      :row-class="() => 'row-clickable'"
      @row-click="drill($event.data as NamedLine, 'supplier')"
    >
      <template #empty><div class="empty small">No suppliers with expenses.</div></template>
      <Column field="name" header="Supplier" sortable>
        <template #body="{ data }"><span :class="{ muted: data.id === null }">{{ data.name }}</span></template>
      </Column>
      <Column field="count" header="Expenses" sortable class="num" />
      <Column field="quoted" header="Open quotes" sortable class="num"><template #body="{ data }">{{ money(data.quoted) }}</template></Column>
      <Column field="committed" header="Committed" sortable class="num"><template #body="{ data }">{{ money(data.committed) }}</template></Column>
      <Column field="paid" header="Paid" sortable class="num"><template #body="{ data }">{{ money(data.paid) }}</template></Column>
      <Column field="outstanding" header="Outstanding" sortable class="num"><template #body="{ data }">{{ money(data.outstanding) }}</template></Column>
      <Column header="" style="width: 28%; min-width: 140px">
        <template #body="{ data }">
          <BudgetBar :paid="data.paid" :outstanding="data.outstanding" :quoted="data.quoted" :estimated="data.estimated" :budget="null" :scale="supplierScale" />
        </template>
      </Column>
      <Column field="last_payment" header="Last payment" sortable><template #body="{ data }">{{ day(data.last_payment) }}</template></Column>
    </DataTable>
  </div>
</template>
