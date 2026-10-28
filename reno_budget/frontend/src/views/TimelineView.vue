<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '@/api'
import DateInput from '@/components/DateInput.vue'
import { useConfirmDelete, useNotify } from '@/composables'
import { day, fromIsoDate, MILESTONE_LABELS, money, todayIso } from '@/format'
import { useAppStore } from '@/stores/app'
import type { BudgetLine, Milestone } from '@/types'

const app = useAppStore()
const notify = useNotify()
const confirmDelete = useConfirmDelete()

const totals = ref<Record<string, BudgetLine>>({})
const DAY = 86_400_000

async function loadTotals() {
  totals.value = await api.get<Record<string, BudgetLine>>('reports/milestones')
}

const milestones = computed(() =>
  [...app.milestones].sort((a, b) =>
    (a.planned_start ?? a.actual_start ?? '9999').localeCompare(b.planned_start ?? b.actual_start ?? '9999'),
  ),
)

// Visible date range: all milestone dates, the project dates and today, padded a little.
const range = computed(() => {
  const dates: string[] = [todayIso()]
  for (const m of app.milestones)
    for (const d of [m.planned_start, m.planned_end, m.actual_start, m.actual_end]) if (d) dates.push(d)
  if (app.settings?.start_date) dates.push(app.settings.start_date)
  if (app.settings?.target_end_date) dates.push(app.settings.target_end_date)
  dates.sort()
  const start = fromIsoDate(dates[0])!
  const end = fromIsoDate(dates[dates.length - 1])!
  start.setDate(1)
  end.setMonth(end.getMonth() + 1, 0)
  return { start: start.getTime(), end: end.getTime() + DAY }
})

const span = computed(() => range.value.end - range.value.start)
const pos = (iso: string) => ((fromIsoDate(iso)!.getTime() - range.value.start) / span.value) * 100

const months = computed(() => {
  const result: { label: string; left: number }[] = []
  const cursor = new Date(range.value.start)
  while (cursor.getTime() < range.value.end) {
    result.push({
      label: cursor.toLocaleDateString(undefined, { month: 'short', year: cursor.getMonth() === 0 ? '2-digit' : undefined }),
      left: ((cursor.getTime() - range.value.start) / span.value) * 100,
    })
    cursor.setMonth(cursor.getMonth() + 1)
  }
  return result
})

const todayLeft = computed(() => pos(todayIso()))

function bar(start: string | null, end: string | null, fallbackEnd?: string) {
  const from = start ?? end
  const to = end ?? fallbackEnd ?? start
  if (!from || !to) return null
  const left = pos(from)
  const right = pos(to) + (DAY / span.value) * 100
  return { left: `${left}%`, width: `${Math.max(right - left, 0.6)}%` }
}

const SEVERITY = { planned: 'secondary', in_progress: 'info', done: 'success', late: 'danger' } as const

// Dialog
const dialogVisible = ref(false)
const editing = ref<Milestone | null>(null)
const blank = () => ({
  name: '',
  room_id: null as number | null,
  planned_start: null as string | null,
  planned_end: null as string | null,
  actual_start: null as string | null,
  actual_end: null as string | null,
  notes: null as string | null,
})
const form = reactive(blank())

function openDialog(milestone: Milestone | null) {
  editing.value = milestone
  Object.assign(form, blank(), milestone ?? {})
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) return
  if (form.planned_start && form.planned_end && form.planned_end < form.planned_start) {
    notify.error('Planned end is before planned start', 'Check the dates')
    return
  }
  try {
    const body = { ...form, name: form.name.trim() }
    if (editing.value) await api.patch(`milestones/${editing.value.id}`, body)
    else await api.post('milestones', { ...body, sort_order: app.milestones.length })
    dialogVisible.value = false
    await app.loadMilestones()
  } catch (error) {
    notify.error(error, 'Could not save milestone')
  }
}

async function quick(milestone: Milestone, field: 'actual_start' | 'actual_end') {
  try {
    const body: Record<string, string> = { [field]: todayIso() }
    if (field === 'actual_end' && !milestone.actual_start) body.actual_start = milestone.planned_start ?? todayIso()
    await api.patch(`milestones/${milestone.id}`, body)
    await app.loadMilestones()
  } catch (error) {
    notify.error(error)
  }
}

function remove(milestone: Milestone) {
  confirmDelete(`Delete milestone “${milestone.name}”? Linked expenses are kept.`, async () => {
    try {
      await api.del(`milestones/${milestone.id}`)
      await app.loadMilestones()
      app.touch()
    } catch (error) {
      notify.error(error)
    }
  })
}

watch(() => app.dataVersion, loadTotals)
onMounted(loadTotals)
</script>

<template>
  <div class="toolbar">
    <div class="legend">
      <span><i class="planned-key" />Planned</span>
      <span><i class="actual-key" />Actual</span>
      <span><i class="today-key" />Today</span>
    </div>
    <span class="spacer" />
    <Button label="New milestone" icon="pi pi-plus" @click="openDialog(null)" />
  </div>

  <div class="card timeline">
    <div v-if="!milestones.length" class="empty">
      <i class="pi pi-calendar" />No milestones yet. Add phases such as demolition, rough-in, plastering, finishing.
    </div>
    <template v-else>
      <div class="tl-row header">
        <div />
        <div class="track axis">
          <span v-for="m in months" :key="m.left" class="tick" :style="{ left: `${m.left}%` }">{{ m.label }}</span>
        </div>
        <div />
      </div>
      <div v-for="m in milestones" :key="m.id" class="tl-row">
        <div class="info">
          <a href="#" class="name" @click.prevent="openDialog(m)">{{ m.name }}</a>
          <div class="row small">
            <Tag :value="MILESTONE_LABELS[m.status]" :severity="SEVERITY[m.status]" :icon="m.status === 'late' ? 'pi pi-exclamation-triangle' : undefined" />
            <span v-if="m.room_id" class="muted">{{ app.roomById.get(m.room_id)?.name }}</span>
          </div>
        </div>
        <div class="track">
          <span v-for="mo in months" :key="mo.left" class="grid-line" :style="{ left: `${mo.left}%` }" />
          <span class="today" :style="{ left: `${todayLeft}%` }" />
          <div
            v-if="bar(m.planned_start, m.planned_end)"
            v-tooltip.top="`Planned: ${day(m.planned_start)} → ${day(m.planned_end)}`"
            class="bar planned"
            :style="bar(m.planned_start, m.planned_end)!"
          />
          <div
            v-if="m.actual_start"
            v-tooltip.top="`Actual: ${day(m.actual_start)} → ${m.actual_end ? day(m.actual_end) : 'ongoing'}`"
            class="bar actual"
            :class="{ ongoing: !m.actual_end }"
            :style="bar(m.actual_start, m.actual_end, todayIso())!"
          />
        </div>
        <div class="side">
          <div v-if="totals[m.id]" class="small num">
            {{ money(totals[m.id]?.forecast) }}
            <div class="muted">paid {{ money(totals[m.id]?.paid) }}</div>
          </div>
          <div class="row">
            <Button v-if="!m.actual_start" v-tooltip.top="'Started today'" icon="pi pi-play" text rounded size="small" @click="quick(m, 'actual_start')" />
            <Button v-else-if="!m.actual_end" v-tooltip.top="'Finished today'" icon="pi pi-check" text rounded size="small" @click="quick(m, 'actual_end')" />
            <Button icon="pi pi-trash" text rounded size="small" severity="danger" aria-label="Delete" @click="remove(m)" />
          </div>
        </div>
      </div>
    </template>
  </div>

  <Dialog v-model:visible="dialogVisible" :header="editing ? 'Edit milestone' : 'New milestone'" modal :style="{ width: '520px' }">
    <form id="milestone-form" class="form-grid" @submit.prevent="save">
      <div class="field full">
        <label for="ms-name">Name</label>
        <InputText id="ms-name" v-model="form.name" autofocus />
      </div>
      <div class="field full">
        <label for="ms-room">Room</label>
        <Select v-model="form.room_id" input-id="ms-room" :options="app.activeRooms" option-label="name" option-value="id" show-clear placeholder="Whole house" />
      </div>
      <div class="field"><label>Planned start</label><DateInput v-model="form.planned_start" /></div>
      <div class="field"><label>Planned end</label><DateInput v-model="form.planned_end" /></div>
      <div class="field"><label>Actual start</label><DateInput v-model="form.actual_start" /></div>
      <div class="field"><label>Actual end</label><DateInput v-model="form.actual_end" /></div>
      <div class="field full">
        <label for="ms-notes">Notes</label>
        <Textarea id="ms-notes" v-model="form.notes" rows="2" auto-resize />
      </div>
      <p class="full muted small" style="margin: 0">
        Link expenses to this milestone from the expense form to see their cost here.
      </p>
    </form>
    <template #footer>
      <Button label="Cancel" severity="secondary" outlined @click="dialogVisible = false" />
      <Button type="submit" form="milestone-form" label="Save" icon="pi pi-check" :disabled="!form.name.trim()" />
    </template>
  </Dialog>
</template>

<style scoped>
.timeline {
  overflow-x: auto;
}
.tl-row {
  display: grid;
  grid-template-columns: 220px minmax(480px, 1fr) 150px;
  gap: 12px;
  align-items: center;
  padding: 8px 0;
  border-top: 1px solid var(--border);
}
.tl-row.header {
  border-top: none;
  padding-top: 0;
}
.info .name {
  color: var(--text);
  font-weight: 600;
  text-decoration: none;
}
.info .row {
  margin-top: 4px;
}
.track {
  position: relative;
  height: 30px;
}
.track.axis {
  height: 18px;
}
.tick {
  position: absolute;
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  padding-left: 3px;
  border-left: 1px solid var(--baseline);
}
.grid-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--grid);
}
.today {
  position: absolute;
  top: -8px;
  bottom: -8px;
  width: 2px;
  background: var(--p-primary-color);
  z-index: 2;
}
.bar {
  position: absolute;
  border-radius: 4px;
}
.bar.planned {
  top: 3px;
  height: 12px;
  background: var(--surface-sunken);
  border: 1px solid var(--baseline);
}
.bar.actual {
  top: 17px;
  height: 10px;
  background: var(--series-1);
}
.bar.actual.ongoing {
  background: repeating-linear-gradient(45deg, var(--series-1) 0 6px, transparent 6px 9px), var(--series-1);
  opacity: 0.85;
}
.side {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}
.planned-key,
.actual-key,
.today-key {
  display: inline-block;
  width: 16px;
  height: 10px;
  border-radius: 3px;
}
.planned-key {
  background: var(--surface-sunken);
  border: 1px solid var(--baseline);
}
.actual-key {
  background: var(--series-1);
}
.today-key {
  width: 2px;
  height: 12px;
  background: var(--p-primary-color);
}
</style>
