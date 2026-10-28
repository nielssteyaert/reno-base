<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useConfirmDelete, useNotify } from '@/composables'
import { day, money } from '@/format'
import { useAppStore } from '@/stores/app'
import type { NamedLine, Supplier } from '@/types'

const app = useAppStore()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()

const figures = ref<NamedLine[]>([])
const search = ref('')
const showArchived = ref(false)

async function loadFigures() {
  figures.value = await api.get<NamedLine[]>('reports/suppliers')
}
const figuresById = computed(() => new Map(figures.value.map((f) => [f.id, f])))

const rows = computed(() => {
  const needle = search.value.trim().toLowerCase()
  return app.suppliers
    .filter((s) => showArchived.value || !s.archived)
    .filter(
      (s) =>
        !needle ||
        [s.name, s.contact_person, s.email, s.phone, s.vat_number].some((v) => v?.toLowerCase().includes(needle)),
    )
    .map((s) => {
      const f = figuresById.value.get(s.id)
      return {
        ...s,
        _count: f?.count ?? 0,
        _committed: f?.committed ?? 0,
        _paid: f?.paid ?? 0,
        _outstanding: f?.outstanding ?? 0,
        _quoted: f?.quoted ?? 0,
        _last: f?.last_payment ?? null,
      }
    })
})

const dialogVisible = ref(false)
const editing = ref<Supplier | null>(null)
const blank = () => ({
  name: '',
  contact_person: null as string | null,
  phone: null as string | null,
  email: null as string | null,
  website: null as string | null,
  address: null as string | null,
  vat_number: null as string | null,
  notes: null as string | null,
  archived: false,
})
const form = reactive(blank())

function openDialog(supplier: Supplier | null) {
  editing.value = supplier
  Object.assign(form, blank(), supplier ?? {})
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) return
  try {
    const body = { ...form, name: form.name.trim() }
    if (editing.value) await api.patch(`suppliers/${editing.value.id}`, body)
    else await api.post('suppliers', body)
    dialogVisible.value = false
    await Promise.all([app.loadSuppliers(), loadFigures()])
  } catch (error) {
    notify.error(error, 'Could not save supplier')
  }
}

function remove(supplier: Supplier) {
  const count = figuresById.value.get(supplier.id)?.count ?? 0
  confirmDelete(
    count
      ? `Delete “${supplier.name}”? ${count} expense(s) will lose their supplier. Archiving keeps them linked.`
      : `Delete “${supplier.name}”?`,
    async () => {
      try {
        await api.del(`suppliers/${supplier.id}`)
        await Promise.all([app.loadSuppliers(), loadFigures()])
        app.touch()
      } catch (error) {
        notify.error(error)
      }
    },
  )
}

watch(() => app.dataVersion, loadFigures)
onMounted(loadFigures)
</script>

<template>
  <div class="toolbar">
    <IconField>
      <InputIcon class="pi pi-search" />
      <InputText v-model="search" placeholder="Search suppliers" />
    </IconField>
    <span class="spacer" />
    <label class="row small"><ToggleSwitch v-model="showArchived" /> Show archived</label>
    <Button label="New supplier" icon="pi pi-plus" @click="openDialog(null)" />
  </div>

  <div class="card" style="padding: 0; overflow: hidden">
    <DataTable
      :value="rows"
      data-key="id"
      size="small"
      sort-field="_committed"
      :sort-order="-1"
      removable-sort
      scrollable
      :row-class="(row: Supplier) => (row.archived ? 'archived-row row-clickable' : 'row-clickable')"
      @row-click="openDialog($event.data as Supplier)"
    >
      <template #empty><div class="empty"><i class="pi pi-users" />No suppliers yet.</div></template>
      <Column field="name" header="Supplier" sortable>
        <template #body="{ data }">
          <strong>{{ data.name }}</strong>
          <div v-if="data.contact_person" class="muted small">{{ data.contact_person }}</div>
        </template>
      </Column>
      <Column header="Contact">
        <template #body="{ data }">
          <div v-if="data.phone"><a :href="`tel:${data.phone}`" @click.stop>{{ data.phone }}</a></div>
          <div v-if="data.email"><a :href="`mailto:${data.email}`" @click.stop>{{ data.email }}</a></div>
        </template>
      </Column>
      <Column field="_count" header="Expenses" sortable class="num" />
      <Column field="_quoted" header="Open quotes" sortable class="num">
        <template #body="{ data }">{{ data._quoted ? money(data._quoted) : '—' }}</template>
      </Column>
      <Column field="_committed" header="Committed" sortable class="num">
        <template #body="{ data }">{{ money(data._committed) }}</template>
      </Column>
      <Column field="_paid" header="Paid" sortable class="num">
        <template #body="{ data }">{{ money(data._paid) }}</template>
      </Column>
      <Column field="_outstanding" header="Outstanding" sortable class="num">
        <template #body="{ data }">{{ data._outstanding ? money(data._outstanding) : '—' }}</template>
      </Column>
      <Column field="_last" header="Last payment" sortable>
        <template #body="{ data }">{{ day(data._last) }}</template>
      </Column>
      <Column style="width: 96px">
        <template #body="{ data }">
          <div class="row" style="justify-content: flex-end">
            <Button
              v-tooltip.top="'Show expenses'"
              icon="pi pi-receipt"
              text
              rounded
              size="small"
              @click.stop="router.push({ path: '/expenses', query: { supplier: data.id } })"
            />
            <Button icon="pi pi-trash" text rounded size="small" severity="danger" aria-label="Delete" @click.stop="remove(data)" />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>

  <Dialog v-model:visible="dialogVisible" :header="editing ? 'Edit supplier' : 'New supplier'" modal :style="{ width: '560px' }">
    <form id="supplier-form" class="form-grid" @submit.prevent="save">
      <div class="field full">
        <label for="sup-name">Name</label>
        <InputText id="sup-name" v-model="form.name" autofocus />
      </div>
      <div class="field">
        <label for="sup-contact">Contact person</label>
        <InputText id="sup-contact" v-model="form.contact_person" />
      </div>
      <div class="field">
        <label for="sup-phone">Phone</label>
        <InputText id="sup-phone" v-model="form.phone" type="tel" />
      </div>
      <div class="field">
        <label for="sup-email">Email</label>
        <InputText id="sup-email" v-model="form.email" type="email" />
      </div>
      <div class="field">
        <label for="sup-web">Website</label>
        <InputText id="sup-web" v-model="form.website" />
      </div>
      <div class="field">
        <label for="sup-vat">VAT number</label>
        <InputText id="sup-vat" v-model="form.vat_number" placeholder="BE0123.456.789" />
      </div>
      <div class="field full">
        <label for="sup-address">Address</label>
        <Textarea id="sup-address" v-model="form.address" rows="2" auto-resize />
      </div>
      <div class="field full">
        <label for="sup-notes">Notes</label>
        <Textarea id="sup-notes" v-model="form.notes" rows="2" auto-resize />
      </div>
      <label v-if="editing" class="row full"><Checkbox v-model="form.archived" binary /> Archived</label>
    </form>
    <template #footer>
      <Button label="Cancel" severity="secondary" outlined @click="dialogVisible = false" />
      <Button type="submit" form="supplier-form" label="Save" icon="pi pi-check" :disabled="!form.name.trim()" />
    </template>
  </Dialog>
</template>

<style scoped>
:deep(.archived-row) {
  opacity: 0.55;
}
</style>
