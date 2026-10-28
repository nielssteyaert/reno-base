<script setup lang="ts">
import { computed } from 'vue'
import { money } from '@/format'

/**
 * Bullet-style budget bar: paid → outstanding → quoted → estimated stacked left to right on a
 * shared scale, with a vertical marker at the budget. Pass the same `scale` to every bar in a
 * list so their lengths are comparable.
 */
const props = withDefaults(
  defineProps<{
    paid: number
    outstanding: number
    quoted: number
    estimated: number
    budget: number | null
    /** Optional second, dashed marker (e.g. the working budget before contingency). */
    reference?: number | null
    referenceLabel?: string
    scale?: number
    height?: number
  }>(),
  { scale: 0, height: 12, reference: null, referenceLabel: 'Working budget' },
)

const segments = computed(() => [
  { key: 'paid', label: 'Paid', value: props.paid, color: 'var(--stack-paid)' },
  { key: 'outstanding', label: 'Committed, unpaid', value: props.outstanding, color: 'var(--stack-outstanding)' },
  { key: 'quoted', label: 'Quoted', value: props.quoted, color: 'var(--stack-quoted)' },
  { key: 'estimated', label: 'Estimated', value: props.estimated, color: 'var(--stack-estimated)' },
])

const total = computed(() => segments.value.reduce((sum, s) => sum + s.value, 0))
const max = computed(() => Math.max(props.scale, props.budget ?? 0, total.value, 1))
const visible = computed(() => segments.value.filter((s) => s.value > 0))
const markerLeft = computed(() => (props.budget ? (props.budget / max.value) * 100 : null))
const referenceLeft = computed(() => (props.reference ? (props.reference / max.value) * 100 : null))

const tooltip = computed(() => {
  const lines = segments.value.map((s) => `${s.label}: ${money(s.value)}`)
  lines.push(`Forecast: ${money(total.value)}`)
  if (props.reference) lines.push(`${props.referenceLabel}: ${money(props.reference)}`)
  if (props.budget) lines.push(`Budget: ${money(props.budget)}`)
  return lines.join('\n')
})
</script>

<template>
  <div
    v-tooltip.top="{ value: tooltip, pt: { text: { style: 'white-space: pre-line' } } }"
    class="budget-bar"
    :style="{ height: `${props.height + 8}px` }"
    role="img"
    :aria-label="tooltip"
  >
    <div class="track" :style="{ height: `${props.height}px` }">
      <div
        v-for="segment in visible"
        :key="segment.key"
        class="segment"
        :style="{ width: `${(segment.value / max) * 100}%`, background: segment.color }"
      />
    </div>
    <div
      v-if="referenceLeft !== null"
      class="marker reference"
      :style="{ left: `calc(${referenceLeft}% - 1px)` }"
    />
    <div v-if="markerLeft !== null" class="marker" :style="{ left: `calc(${markerLeft}% - 1px)` }" />
  </div>
</template>

<style scoped>
.budget-bar {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  cursor: default;
}
.track {
  display: flex;
  gap: 2px;
  width: 100%;
  background: var(--surface-sunken);
  border-radius: 4px;
  overflow: hidden;
}
.segment {
  height: 100%;
  min-width: 2px;
}
.segment:last-child {
  border-radius: 0 4px 4px 0;
}
.marker {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  border-radius: 1px;
  background: var(--budget-marker);
  box-shadow: 0 0 0 2px var(--surface);
}
.marker.reference {
  background: repeating-linear-gradient(
    to bottom,
    var(--budget-marker) 0 3px,
    transparent 3px 5px
  );
  box-shadow: none;
}
</style>
