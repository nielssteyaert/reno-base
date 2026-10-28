<script setup lang="ts">
import { HEALTH_ICONS, HEALTH_LABELS } from '@/format'
import type { Health } from '@/types'

const props = defineProps<{ health: Health }>()
</script>

<template>
  <span class="health" :class="props.health">
    <i :class="HEALTH_ICONS[props.health]" />{{ HEALTH_LABELS[props.health] }}
  </span>
</template>
