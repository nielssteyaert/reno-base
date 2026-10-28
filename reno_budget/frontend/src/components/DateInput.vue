<script setup lang="ts">
import DatePicker from 'primevue/datepicker'
import { computed } from 'vue'
import { fromIsoDate, toIsoDate } from '@/format'

/** Date picker bound to an ISO "YYYY-MM-DD" string. */
const props = defineProps<{ placeholder?: string; inputId?: string }>()
const iso = defineModel<string | null>({ default: null })

const value = computed({
  get: () => fromIsoDate(iso.value),
  set: (date: Date | Date[] | (Date | null)[] | null | undefined) =>
    (iso.value = date instanceof Date ? toIsoDate(date) : null),
})
</script>

<template>
  <DatePicker
    v-model="value"
    date-format="dd/mm/yy"
    show-icon
    icon-display="input"
    show-button-bar
    :input-id="props.inputId"
    :placeholder="props.placeholder"
    fluid
  />
</template>
