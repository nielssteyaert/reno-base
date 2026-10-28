<script setup lang="ts">
import Button from 'primevue/button'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import { onMounted, ref, watch } from 'vue'
import { api } from '@/api'
import HistoryList from '@/components/HistoryList.vue'
import { useNotify } from '@/composables'
import { useAppStore } from '@/stores/app'
import type { AuditEntry } from '@/types'

const app = useAppStore()
const notify = useNotify()
const PAGE = 50

const entries = ref<AuditEntry[]>([])
const total = ref(0)
const entityType = ref<string | null>(null)
const search = ref('')
const loading = ref(false)

const entityOptions = [
  { value: 'expense', label: 'Expenses' },
  { value: 'payment', label: 'Payments' },
  { value: 'attachment', label: 'Files' },
  { value: 'category', label: 'Categories' },
  { value: 'room', label: 'Rooms' },
  { value: 'supplier', label: 'Suppliers' },
  { value: 'milestone', label: 'Milestones' },
  { value: 'settings', label: 'Settings' },
]

async function load(append = false) {
  loading.value = true
  try {
    const page = await api.get<{ items: AuditEntry[]; total: number }>('audit', {
      entity_type: entityType.value,
      q: search.value.trim() || null,
      limit: PAGE,
      offset: append ? entries.value.length : 0,
    })
    entries.value = append ? [...entries.value, ...page.items] : page.items
    total.value = page.total
  } catch (error) {
    notify.error(error)
  } finally {
    loading.value = false
  }
}

let timer: ReturnType<typeof setTimeout> | undefined
watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(() => load(), 300)
})
watch(entityType, () => load())
watch(() => app.dataVersion, () => load())
onMounted(() => load())
</script>

<template>
  <div class="toolbar">
    <IconField>
      <InputIcon class="pi pi-search" />
      <InputText v-model="search" placeholder="Search name or user" />
    </IconField>
    <Select v-model="entityType" :options="entityOptions" option-label="label" option-value="value" show-clear placeholder="Everything" />
    <span class="spacer" />
    <span class="muted small">{{ total }} change(s)</span>
  </div>
  <div class="card">
    <HistoryList :entries="entries" />
    <div v-if="entries.length < total" class="row" style="justify-content: center; margin-top: 16px">
      <Button label="Load more" severity="secondary" outlined :loading="loading" @click="load(true)" />
    </div>
  </div>
</template>
