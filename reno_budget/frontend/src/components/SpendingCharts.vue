<script setup lang="ts">
import Chart from 'primevue/chart'
import { computed } from 'vue'
import { money, moneyCompact, monthLabel } from '@/format'
import type { MonthRow } from '@/types'
import { useChartTheme } from './useChartTheme'

/**
 * Two charts on one scale each (never a dual axis): cumulative spend against the budget line,
 * and monthly paid vs committed.
 */
const props = defineProps<{ months: MonthRow[]; budget: number }>()
const theme = useChartTheme()

const labels = computed(() => props.months.map((m) => monthLabel(m.month)))

function baseOptions() {
  const c = theme.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index' as const, intersect: false },
    plugins: {
      legend: {
        position: 'top' as const,
        align: 'end' as const,
        labels: { color: c.text, boxWidth: 12, boxHeight: 12, usePointStyle: true },
      },
      tooltip: {
        callbacks: {
          label: (ctx: { dataset: { label?: string }; parsed: { y: number | null } }) =>
            `${ctx.dataset.label}: ${money(ctx.parsed.y ?? 0)}`,
        },
      },
    },
    scales: {
      x: { grid: { display: false }, border: { color: c.baseline }, ticks: { color: c.muted } },
      y: {
        beginAtZero: true,
        grid: { color: c.grid },
        border: { display: false },
        ticks: { color: c.muted, callback: (value: number | string) => moneyCompact(Number(value)) },
      },
    },
  }
}

const cumulativeData = computed(() => {
  const c = theme.value
  const datasets: object[] = [
    {
      label: 'Paid (cumulative)',
      data: props.months.map((m) => m.cumulative_paid),
      borderColor: c.series1,
      backgroundColor: c.series1,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 5,
      pointStyle: 'circle',
      cubicInterpolationMode: 'monotone',
    },
    {
      label: 'Committed (cumulative)',
      data: props.months.map((m) => m.cumulative_committed),
      borderColor: c.series2,
      backgroundColor: c.series2,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 5,
      pointStyle: 'circle',
      cubicInterpolationMode: 'monotone',
    },
  ]
  if (props.budget) {
    datasets.push({
      label: 'Total budget',
      data: props.months.map(() => props.budget),
      borderColor: c.ink,
      backgroundColor: c.ink,
      borderWidth: 1.5,
      borderDash: [6, 4],
      pointRadius: 0,
      pointHoverRadius: 0,
      pointStyle: 'line',
    })
  }
  return { labels: labels.value, datasets }
})

const monthlyData = computed(() => {
  const c = theme.value
  const bar = { borderRadius: 4, borderSkipped: 'start' as const, maxBarThickness: 28, categoryPercentage: 0.7, barPercentage: 0.9 }
  return {
    labels: labels.value,
    datasets: [
      { label: 'Paid', data: props.months.map((m) => m.paid), backgroundColor: c.series1, pointStyle: 'rect', ...bar },
      { label: 'Committed', data: props.months.map((m) => m.committed), backgroundColor: c.series2, pointStyle: 'rect', ...bar },
    ],
  }
})
</script>

<template>
  <div class="grid grid-2">
    <div class="card">
      <h2>Cumulative spending</h2>
      <div class="chart"><Chart type="line" :data="cumulativeData" :options="baseOptions()" /></div>
    </div>
    <div class="card">
      <h2>Per month</h2>
      <div class="chart"><Chart type="bar" :data="monthlyData" :options="baseOptions()" /></div>
    </div>
  </div>
</template>

<style scoped>
.chart {
  position: relative;
  height: 300px;
}
.chart :deep(.p-chart) {
  height: 100%;
}
</style>
