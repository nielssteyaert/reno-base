<script setup lang="ts">
import InputNumber from 'primevue/inputnumber'
import { computed } from 'vue'
import { currentCurrency, currentLocale } from '@/format'

/** Currency input bound to integer cents. */
const props = defineProps<{ placeholder?: string; inputId?: string; invalid?: boolean }>()
const cents = defineModel<number | null>({ default: null })

const euros = computed({
  get: () => (cents.value === null ? null : cents.value / 100),
  set: (value: number | null) => (cents.value = value === null ? null : Math.round(value * 100)),
})
</script>

<template>
  <InputNumber
    v-model="euros"
    mode="currency"
    :currency="currentCurrency()"
    :locale="currentLocale()"
    :min="0"
    :input-id="props.inputId"
    :placeholder="props.placeholder"
    :invalid="props.invalid"
    fluid
  />
</template>
