<script setup lang="ts">
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import BudgetBar from '@/components/BudgetBar.vue'
import BudgetLegend from '@/components/BudgetLegend.vue'
import BudgetTable from '@/components/BudgetTable.vue'
import HistoryList from '@/components/HistoryList.vue'
import KpiTile from '@/components/KpiTile.vue'
import { useNotify } from '@/composables'
import { day, MILESTONE_LABELS, money, pct, STATUS_LABELS } from '@/format'
import { useAppStore } from '@/stores/app'
import { useDrawerStore } from '@/stores/drawer'
import type { Dashboard, NamedLine } from '@/types'

const app = useAppStore()
const drawer = useDrawerStore()
const router = useRouter()
const notify = useNotify()
const data = ref<Dashboard | null>(null)

async function load() {
  try {
    data.value = await api.get<Dashboard>('reports/dashboard')
  } catch (error) {
    notify.error(error, 'Could not load dashboard')
  }
}

const s = computed(() => data.value?.summary)
const hasBudget = computed(() => (s.value?.budget ?? 0) > 0)
const isEmpty = computed(() => s.value && s.value.count === 0 && !hasBudget.value)

const forecastTone = computed(() => {
  if (!s.value || !hasBudget.value) return undefined
  if (s.value.over_budget) return 'critical'
  if (s.value.uses_contingency) return 'warning'
  return 'good'
})

const forecastSub = computed(() => {
  if (!s.value || !hasBudget.value) return 'Set a budget in Settings'
  if (s.value.over_budget) return `Over budget by ${money(-(s.value.remaining ?? 0))}`
  if (s.value.uses_contingency) return `Uses ${money(s.value.contingency_used)} of the contingency`
  return `${pct(s.value.pct_forecast)} of budget`
})

const funnelMax = computed(() => Math.max(1, ...(s.value?.funnel.map((f) => f.amount) ?? [0])))

function openCategory(row: NamedLine) {
  router.push({ path: '/expenses', query: row.id === null ? {} : { category: row.id } })
}
function openRoom(row: NamedLine) {
  router.push({ path: '/expenses', query: row.id === null ? {} : { room: row.id } })
}

const MILESTONE_SEVERITY = { planned: 'secondary', in_progress: 'info', done: 'success', late: 'danger' } as const

watch(() => app.dataVersion, load)
onMounted(load)
</script>

<template>
  <div v-if="!data" class="empty">Loading…</div>
  <div v-else class="stack">
    <div v-if="isEmpty" class="card onboarding">
      <h2>Welcome! Let's set up your renovation budget</h2>
      <ol>
        <li>Set your total budget and contingency in <RouterLink to="/settings">Settings</RouterLink>.</li>
        <li>Create <RouterLink to="/categories">categories</RouterLink> and <RouterLink to="/rooms">rooms</RouterLink>, optionally with their own budgets.</li>
        <li>Add expenses as estimates, then move them through quote → ordered → invoiced, and record payments.</li>
      </ol>
      <div class="row">
        <Button label="Add an expense" icon="pi pi-plus" @click="drawer.create()" />
        <Button label="Import a spreadsheet" icon="pi pi-upload" severity="secondary" outlined @click="router.push('/import')" />
      </div>
    </div>

    <div class="kpis">
      <KpiTile
        label="Total budget"
        icon="pi pi-wallet"
        :value="money(s!.budget ?? 0)"
        :sub="hasBudget ? `Incl. ${money(s!.contingency_reserve)} contingency` : 'Not set yet'"
      />
      <KpiTile label="Forecast" icon="pi pi-chart-line" :value="money(s!.forecast)" :sub="forecastSub" :tone="forecastTone" />
      <KpiTile
        label="Committed"
        icon="pi pi-file-check"
        :value="money(s!.committed)"
        :sub="hasBudget ? `${pct(s!.pct_committed)} of budget` : `${s!.count} expenses`"
      />
      <KpiTile label="Paid" icon="pi pi-credit-card" :value="money(s!.paid)" :sub="`${money(s!.outstanding)} still to pay`" />
      <KpiTile
        label="Remaining"
        icon="pi pi-flag"
        :value="money(s!.remaining)"
        :sub="hasBudget ? 'Budget minus forecast' : undefined"
        :tone="s!.remaining !== null && s!.remaining < 0 ? 'critical' : undefined"
      />
    </div>

    <div class="card">
      <div class="card-head">
        <h2>Project budget</h2>
        <BudgetLegend />
      </div>
      <BudgetBar
        :paid="s!.paid"
        :outstanding="s!.outstanding"
        :quoted="s!.quoted"
        :estimated="s!.estimated"
        :budget="s!.budget"
        :reference="hasBudget && s!.contingency_reserve ? s!.working_budget : null"
        :height="22"
      />
      <div class="muted small bar-notes">
        <span>Working budget {{ money(s!.working_budget) }} (dashed) + contingency {{ money(s!.contingency_reserve) }}</span>
        <span v-if="s!.allocated_budget">
          Allocated to categories {{ money(s!.allocated_budget) }} ·
          <span :class="{ warn: s!.unallocated_budget < 0 }">unallocated {{ money(s!.unallocated_budget) }}</span>
        </span>
      </div>
    </div>

    <div class="grid grid-2">
      <div class="card">
        <div class="card-head">
          <h2>Categories</h2>
          <Button label="Report" icon="pi pi-arrow-right" icon-pos="right" text size="small" @click="router.push('/reports/budget')" />
        </div>
        <BudgetTable v-if="data.categories.length" :rows="data.categories.filter((c) => c.count || c.budget)" compact name-header="Category" @select="openCategory" />
        <div v-else class="empty small">No categories yet.</div>
      </div>
      <div class="card">
        <div class="card-head">
          <h2>Rooms</h2>
          <Button label="Report" icon="pi pi-arrow-right" icon-pos="right" text size="small" @click="router.push('/reports/budget')" />
        </div>
        <BudgetTable v-if="data.rooms.length" :rows="data.rooms.filter((r) => r.count || r.budget)" compact name-header="Room" @select="openRoom" />
        <div v-else class="empty small">No rooms yet.</div>
      </div>
    </div>

    <div class="grid grid-3">
      <div class="card">
        <h2>Expense lifecycle</h2>
        <ul class="funnel">
          <li v-for="step in s!.funnel" :key="step.status">
            <RouterLink :to="{ path: '/expenses', query: { status: step.status } }" class="funnel-label">
              {{ STATUS_LABELS[step.status] }}
              <span class="muted">({{ step.count }})</span>
            </RouterLink>
            <div class="funnel-track">
              <div class="funnel-bar" :style="{ width: `${(step.amount / funnelMax) * 100}%` }" />
            </div>
            <span class="num">{{ money(step.amount) }}</span>
          </li>
        </ul>
      </div>

      <div class="card">
        <h2>Payments due</h2>
        <div v-if="!data.due.length" class="empty small">Nothing due.</div>
        <ul v-else class="list">
          <li v-for="item in data.due" :key="item.id">
            <a href="#" @click.prevent="drawer.open(item.id)">{{ item.title }}</a>
            <span class="num">{{ money(item.outstanding) }}</span>
            <span class="small" :class="item.overdue ? 'overdue' : 'muted'">
              <i v-if="item.overdue" class="pi pi-exclamation-circle" />
              {{ item.overdue ? 'Overdue since' : 'Due' }} {{ day(item.due_date) }}
            </span>
          </li>
        </ul>
      </div>

      <div class="card">
        <div class="card-head">
          <h2>Next milestones</h2>
          <Button label="Timeline" icon="pi pi-arrow-right" icon-pos="right" text size="small" @click="router.push('/timeline')" />
        </div>
        <div v-if="!data.milestones.length" class="empty small">No open milestones.</div>
        <ul v-else class="list">
          <li v-for="m in data.milestones" :key="m.id">
            <span>{{ m.name }}</span>
            <Tag :value="MILESTONE_LABELS[m.status]" :severity="MILESTONE_SEVERITY[m.status]" />
            <span class="muted small">{{ day(m.planned_start) }} → {{ day(m.planned_end) }}</span>
          </li>
        </ul>
      </div>
    </div>

    <div class="card">
      <div class="card-head">
        <h2>Recent activity</h2>
        <Button label="All history" icon="pi pi-arrow-right" icon-pos="right" text size="small" @click="router.push('/history')" />
      </div>
      <HistoryList :entries="data.recent" />
    </div>
  </div>
</template>

<style scoped>
.onboarding ol {
  margin: 0 0 16px;
  padding-left: 20px;
  line-height: 1.8;
}
.bar-notes {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  margin-top: 8px;
}
.warn {
  color: var(--status-critical-text);
}
.funnel {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.funnel li {
  display: grid;
  grid-template-columns: 110px 1fr auto;
  align-items: center;
  gap: 10px;
}
.funnel-label {
  text-decoration: none;
  color: var(--text);
  font-weight: 550;
}
.funnel-track {
  height: 10px;
  background: var(--surface-sunken);
  border-radius: 4px;
  overflow: hidden;
}
.funnel-bar {
  height: 100%;
  background: var(--stack-outstanding);
  border-radius: 0 4px 4px 0;
}
.list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.list li {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2px 8px;
  align-items: center;
}
.list li > :last-child {
  grid-column: 1 / -1;
}
.overdue {
  color: var(--status-critical-text);
  font-weight: 600;
}
</style>
