<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import BudgetBar from '@/components/BudgetBar.vue'
import BudgetLegend from '@/components/BudgetLegend.vue'
import ColorSwatches from '@/components/ColorSwatches.vue'
import HealthBadge from '@/components/HealthBadge.vue'
import MoneyInput from '@/components/MoneyInput.vue'
import { useConfirmDelete, useNotify } from '@/composables'
import { money } from '@/format'
import { useAppStore } from '@/stores/app'
import type { NamedLine, Room } from '@/types'

const app = useAppStore()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()

const figures = ref<NamedLine[]>([])
const showArchived = ref(false)

async function loadFigures() {
  figures.value = await api.get<NamedLine[]>('reports/rooms')
}

const figuresById = computed(() => new Map(figures.value.map((f) => [f.id, f])))
const unassigned = computed(() => figures.value.find((f) => f.id === null))
const rooms = computed(() => app.rooms.filter((r) => showArchived.value || !r.archived))
const scale = computed(() => Math.max(1, ...figures.value.map((r) => Math.max(r.budget ?? 0, r.forecast))))

const dialogVisible = ref(false)
const editing = ref<Room | null>(null)
const form = reactive({
  name: '',
  color: null as string | null,
  budget_cents: null as number | null,
  notes: null as string | null,
  archived: false,
})

function openDialog(room: Room | null) {
  editing.value = room
  Object.assign(form, {
    name: room?.name ?? '',
    color: room?.color ?? null,
    budget_cents: room?.budget_cents ?? null,
    notes: room?.notes ?? null,
    archived: room?.archived ?? false,
  })
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) return
  try {
    const body = { ...form, name: form.name.trim() }
    if (editing.value) await api.patch(`rooms/${editing.value.id}`, body)
    else await api.post('rooms', { ...body, sort_order: app.rooms.length })
    dialogVisible.value = false
    await Promise.all([app.loadRooms(), loadFigures()])
  } catch (error) {
    notify.error(error, 'Could not save room')
  }
}

function remove(room: Room) {
  const count = figuresById.value.get(room.id)?.count ?? 0
  const message = count
    ? `Delete “${room.name}”? ${count} expense(s) will no longer have a room. Archiving keeps them linked.`
    : `Delete “${room.name}”?`
  confirmDelete(message, async () => {
    try {
      await api.del(`rooms/${room.id}`)
      await Promise.all([app.loadRooms(), loadFigures()])
      app.touch()
    } catch (error) {
      notify.error(error)
    }
  })
}

async function move(index: number, delta: number) {
  const list = [...rooms.value]
  const target = index + delta
  if (target < 0 || target >= list.length) return
  const [item] = list.splice(index, 1)
  list.splice(target, 0, item!)
  try {
    await Promise.all(list.map((r, i) => api.patch(`rooms/${r.id}`, { sort_order: i })))
    await app.loadRooms()
  } catch (error) {
    notify.error(error)
  }
}

watch(() => app.dataVersion, loadFigures)
onMounted(loadFigures)
</script>

<template>
  <div class="toolbar">
    <span class="muted">Rooms are a second way to slice costs, next to categories.</span>
    <span class="spacer" />
    <label class="row small"><ToggleSwitch v-model="showArchived" /> Show archived</label>
    <Button label="New room" icon="pi pi-plus" @click="openDialog(null)" />
  </div>

  <div class="card">
    <div class="card-head">
      <span class="muted small">Budgets incl. VAT.</span>
      <BudgetLegend />
    </div>
    <div v-if="!rooms.length" class="empty"><i class="pi pi-building" />No rooms yet: kitchen, bathroom, living room, garden…</div>
    <div v-for="(room, index) in rooms" :key="room.id" class="room-row" :class="{ archived: room.archived }">
      <div class="name">
        <i class="swatch" :style="{ background: room.color ?? 'var(--baseline)' }" />
        <a href="#" @click.prevent="router.push({ path: '/expenses', query: { room: room.id } })">{{ room.name }}</a>
        <span v-if="room.archived" class="muted small">(archived)</span>
      </div>
      <div class="num">
        <div>{{ money(figuresById.get(room.id)?.forecast ?? 0) }}</div>
        <div class="muted small">of {{ money(room.budget_cents) }}</div>
      </div>
      <BudgetBar
        v-if="figuresById.get(room.id)"
        v-bind="{
          paid: figuresById.get(room.id)!.paid,
          outstanding: figuresById.get(room.id)!.outstanding,
          quoted: figuresById.get(room.id)!.quoted,
          estimated: figuresById.get(room.id)!.estimated,
          budget: figuresById.get(room.id)!.budget,
        }"
        :scale="scale"
      />
      <div v-else />
      <HealthBadge :health="figuresById.get(room.id)?.health ?? 'none'" />
      <div class="actions">
        <Button icon="pi pi-arrow-up" text rounded size="small" aria-label="Move up" :disabled="index === 0" @click="move(index, -1)" />
        <Button icon="pi pi-arrow-down" text rounded size="small" aria-label="Move down" :disabled="index === rooms.length - 1" @click="move(index, 1)" />
        <Button icon="pi pi-pencil" text rounded size="small" aria-label="Edit" @click="openDialog(room)" />
        <Button icon="pi pi-trash" text rounded size="small" severity="danger" aria-label="Delete" @click="remove(room)" />
      </div>
    </div>
    <div v-if="unassigned" class="room-row">
      <div class="name muted">No room</div>
      <div class="num">{{ money(unassigned.forecast) }}</div>
      <BudgetBar
        :paid="unassigned.paid"
        :outstanding="unassigned.outstanding"
        :quoted="unassigned.quoted"
        :estimated="unassigned.estimated"
        :budget="null"
        :scale="scale"
      />
      <div /><div />
    </div>
  </div>

  <Dialog v-model:visible="dialogVisible" :header="editing ? 'Edit room' : 'New room'" modal :style="{ width: '440px' }">
    <form id="room-form" class="stack" @submit.prevent="save">
      <div class="field">
        <label for="room-name">Name</label>
        <InputText id="room-name" v-model="form.name" autofocus />
      </div>
      <div class="field">
        <label for="room-budget">Budget (incl. VAT)</label>
        <MoneyInput v-model="form.budget_cents" input-id="room-budget" placeholder="No budget" />
      </div>
      <div class="field">
        <label>Colour</label>
        <ColorSwatches v-model="form.color" />
      </div>
      <div class="field">
        <label for="room-notes">Notes</label>
        <Textarea id="room-notes" v-model="form.notes" rows="2" auto-resize />
      </div>
      <label v-if="editing" class="row"><Checkbox v-model="form.archived" binary /> Archived</label>
    </form>
    <template #footer>
      <Button label="Cancel" severity="secondary" outlined @click="dialogVisible = false" />
      <Button type="submit" form="room-form" label="Save" icon="pi pi-check" :disabled="!form.name.trim()" />
    </template>
  </Dialog>
</template>

<style scoped>
.room-row {
  display: grid;
  grid-template-columns: minmax(160px, 1.2fr) 130px minmax(140px, 2fr) 120px auto;
  align-items: center;
  gap: 16px;
  padding: 10px 4px;
  border-top: 1px solid var(--border);
}
.room-row:first-of-type {
  border-top: none;
}
.room-row.archived {
  opacity: 0.55;
}
.name {
  display: flex;
  align-items: center;
  gap: 8px;
}
.name a {
  color: var(--text);
  text-decoration: none;
  font-weight: 600;
}
.actions {
  display: flex;
  justify-content: flex-end;
}
@media (max-width: 900px) {
  .room-row {
    grid-template-columns: 1fr auto;
  }
  .room-row > :nth-child(3),
  .room-row > :nth-child(4) {
    grid-column: 1 / -1;
  }
}
</style>
