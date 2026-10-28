<script setup lang="ts">
import Tag from 'primevue/tag'
import { STATUS_LABELS } from '@/format'
import type { Status } from '@/types'

const props = defineProps<{ status: Status }>()

const STYLE: Record<Status, { severity: string; icon: string }> = {
  estimate: { severity: 'secondary', icon: 'pi pi-pencil' },
  quote: { severity: 'info', icon: 'pi pi-file' },
  ordered: { severity: 'contrast', icon: 'pi pi-shopping-cart' },
  invoiced: { severity: 'warn', icon: 'pi pi-envelope' },
  paid: { severity: 'success', icon: 'pi pi-check' },
}
</script>

<template>
  <Tag
    :severity="STYLE[props.status].severity"
    :icon="STYLE[props.status].icon"
    :value="STATUS_LABELS[props.status]"
  />
</template>
