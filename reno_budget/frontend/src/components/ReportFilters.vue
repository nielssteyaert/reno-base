<script setup lang="ts">
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import MultiSelect from 'primevue/multiselect'
import { computed, ref, watch } from 'vue'
import { STATUS_OPTIONS, toIsoDate } from '@/format'
import { useAppStore } from '@/stores/app'
import type { ReportFilters, Status } from '@/types'

/** One row of report filters; emits the API query shape. */
const filters = defineModel<ReportFilters>({ required: true })
const app = useAppStore()

const range = ref<Date[] | null>(null)
const categoryIds = ref<number[]>([])
const roomIds = ref<number[]>([])
const supplierIds = ref<number[]>([])
const statuses = ref<Status[]>([])

watch([range, categoryIds, roomIds, supplierIds, statuses], () => {
  const [from, to] = range.value ?? []
  filters.value = {
    date_from: from ? toIsoDate(from) : null,
    date_to: to ? toIsoDate(to) : from ? toIsoDate(from) : null,
    category_id: categoryIds.value,
    room_id: roomIds.value,
    supplier_id: supplierIds.value,
    status: statuses.value,
  }
})

const active = computed(
  () =>
    !!range.value ||
    categoryIds.value.length + roomIds.value.length + supplierIds.value.length + statuses.value.length > 0,
)

function clear() {
  range.value = null
  categoryIds.value = []
  roomIds.value = []
  supplierIds.value = []
  statuses.value = []
}
</script>

<template>
  <div class="toolbar filters">
    <DatePicker
      v-model="range"
      selection-mode="range"
      :manual-input="false"
      placeholder="All dates"
      show-button-bar
      date-format="dd/mm/yy"
      style="width: 210px"
    />
    <MultiSelect
      v-model="categoryIds"
      :options="app.categoryOptions()"
      option-label="label"
      option-value="value"
      placeholder="All categories"
      filter
      :max-selected-labels="1"
      selected-items-label="{0} categories"
    />
    <MultiSelect
      v-model="roomIds"
      :options="app.rooms"
      option-label="name"
      option-value="id"
      placeholder="All rooms"
      :max-selected-labels="1"
      selected-items-label="{0} rooms"
    />
    <MultiSelect
      v-model="supplierIds"
      :options="app.suppliers"
      option-label="name"
      option-value="id"
      placeholder="All suppliers"
      filter
      :max-selected-labels="1"
      selected-items-label="{0} suppliers"
    />
    <MultiSelect
      v-model="statuses"
      :options="STATUS_OPTIONS"
      option-label="label"
      option-value="value"
      placeholder="All statuses"
      :max-selected-labels="2"
    />
    <Button v-if="active" label="Clear" icon="pi pi-filter-slash" text @click="clear" />
    <slot />
  </div>
</template>
