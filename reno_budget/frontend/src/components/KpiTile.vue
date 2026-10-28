<script setup lang="ts">
const props = defineProps<{
  label: string
  value: string
  sub?: string
  icon?: string
  tone?: 'good' | 'warning' | 'critical'
}>()
</script>

<template>
  <div class="kpi card">
    <div class="kpi-label">
      <i v-if="props.icon" :class="props.icon" />
      {{ props.label }}
    </div>
    <div class="kpi-value">{{ props.value }}</div>
    <div v-if="props.sub" class="kpi-sub" :class="props.tone">
      <i v-if="props.tone === 'critical'" class="pi pi-times-circle" />
      <i v-else-if="props.tone === 'warning'" class="pi pi-exclamation-triangle" />
      <i v-else-if="props.tone === 'good'" class="pi pi-check-circle" />
      {{ props.sub }}
    </div>
  </div>
</template>

<style scoped>
.kpi {
  padding: 14px 16px;
}
.kpi-label {
  font-size: 12px;
  color: var(--text-2);
  display: flex;
  align-items: center;
  gap: 6px;
}
.kpi-value {
  font-size: 22px;
  font-weight: 650;
  margin-top: 6px;
  white-space: nowrap;
}
.kpi-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  display: flex;
  gap: 4px;
  align-items: center;
}
.kpi-sub.good {
  color: var(--status-good-text);
}
.kpi-sub.warning {
  color: var(--status-warning-text);
}
.kpi-sub.critical {
  color: var(--status-critical-text);
}
</style>
