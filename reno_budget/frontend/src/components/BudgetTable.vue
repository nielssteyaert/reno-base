<script setup lang="ts">
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import { computed } from 'vue'
import { money, pct } from '@/format'
import type { NamedLine } from '@/types'
import BudgetBar from './BudgetBar.vue'
import HealthBadge from './HealthBadge.vue'

/** Budget vs actual table with an in-row bar. Child rows (subcategories) are indented. */
const props = withDefaults(
  defineProps<{ rows: NamedLine[]; compact?: boolean; nameHeader?: string }>(),
  { compact: false, nameHeader: 'Name' },
)
const emit = defineEmits<{ select: [row: NamedLine] }>()

type FlatRow = NamedLine & { depth: number; key: string }

const flat = computed<FlatRow[]>(() =>
  props.rows.flatMap((row) => [
    { ...row, depth: 0, key: `p${row.id}` },
    ...(row.children ?? [])
      .filter((child) => child.count > 0 || child.budget)
      .map((child) => ({ ...child, depth: 1, key: `c${child.id}` })),
  ]),
)

const scale = computed(() =>
  Math.max(1, ...props.rows.map((r) => Math.max(r.budget ?? 0, r.forecast))),
)
</script>

<template>
  <DataTable
    :value="flat"
    data-key="key"
    size="small"
    scrollable
    :row-class="() => 'row-clickable'"
    @row-click="emit('select', $event.data as NamedLine)"
  >
    <Column :header="props.nameHeader" style="min-width: 160px">
      <template #body="{ data }">
        <span class="row" :style="{ paddingLeft: `${data.depth * 18}px` }">
          <i v-if="data.color" class="swatch" :style="{ background: data.color }" />
          <span :class="{ muted: data.id === null }">{{ data.name }}</span>
        </span>
      </template>
    </Column>
    <Column v-if="props.compact" header="Forecast" class="num">
      <template #body="{ data }">
        <div>{{ money(data.forecast) }}</div>
        <div v-if="data.budget" class="muted small">of {{ money(data.budget) }}</div>
      </template>
    </Column>
    <Column v-if="!props.compact" header="Budget" class="num">
      <template #body="{ data }">{{ money(data.budget) }}</template>
    </Column>
    <Column v-if="!props.compact" header="Forecast" class="num">
      <template #body="{ data }">{{ money(data.forecast) }}</template>
    </Column>
    <Column v-if="!props.compact" header="Committed" class="num">
      <template #body="{ data }">{{ money(data.committed) }}</template>
    </Column>
    <Column v-if="!props.compact" header="Paid" class="num">
      <template #body="{ data }">{{ money(data.paid) }}</template>
    </Column>
    <Column v-if="!props.compact" header="Remaining" class="num">
      <template #body="{ data }">
        <span :class="{ 'over-text': data.remaining !== null && data.remaining < 0 }">
          {{ money(data.remaining) }}
        </span>
      </template>
    </Column>
    <Column header="" style="width: 32%; min-width: 140px">
      <template #body="{ data }">
        <BudgetBar
          :paid="data.paid"
          :outstanding="data.outstanding"
          :quoted="data.quoted"
          :estimated="data.estimated"
          :budget="data.budget"
          :scale="scale"
          :height="data.depth ? 8 : 12"
        />
      </template>
    </Column>
    <Column v-if="!props.compact" header="% of budget" class="num">
      <template #body="{ data }">{{ pct(data.pct_forecast) }}</template>
    </Column>
    <Column header="Status">
      <template #body="{ data }"><HealthBadge :health="data.health" /></template>
    </Column>
  </DataTable>
</template>

<style scoped>
.over-text {
  color: var(--status-critical-text);
  font-weight: 600;
}
</style>
