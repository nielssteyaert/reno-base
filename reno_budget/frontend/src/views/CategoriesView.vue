<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
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
import type { Category, NamedLine } from '@/types'

const app = useAppStore()
const router = useRouter()
const notify = useNotify()
const confirmDelete = useConfirmDelete()

const figures = ref<NamedLine[]>([])
const showArchived = ref(false)

async function loadFigures() {
  figures.value = await api.get<NamedLine[]>('reports/categories')
}

const figuresById = computed(() => {
  const map = new Map<number, NamedLine>()
  for (const row of figures.value) {
    if (row.id !== null) map.set(row.id, row)
    for (const child of row.children ?? []) if (child.id !== null) map.set(child.id, child)
  }
  return map
})

const tree = computed(() =>
  app.topCategories
    .filter((c) => showArchived.value || !c.archived)
    .map((parent) => ({
      category: parent,
      children: app.childrenOf(parent.id).filter((c) => showArchived.value || !c.archived),
    })),
)

const scale = computed(() =>
  Math.max(1, ...figures.value.map((r) => Math.max(r.budget ?? 0, r.forecast))),
)

const working = computed(() => {
  const s = app.settings
  if (!s) return 0
  return s.total_budget_cents - Math.round((s.total_budget_cents * s.contingency_pct) / 100)
})
const allocated = computed(() =>
  app.topCategories.filter((c) => !c.archived).reduce((sum, c) => sum + (c.budget_cents ?? 0), 0),
)

// Edit dialog
const dialogVisible = ref(false)
const editing = ref<Category | null>(null)
const form = reactive({
  name: '',
  parent_id: null as number | null,
  color: null as string | null,
  budget_cents: null as number | null,
  notes: null as string | null,
  archived: false,
})
const parentOptions = computed(() =>
  app.topCategories.filter((c) => c.id !== editing.value?.id && !c.archived),
)
const canHaveParent = computed(() => !editing.value || app.childrenOf(editing.value.id).length === 0)

function openDialog(category: Category | null, parentId: number | null = null) {
  editing.value = category
  Object.assign(form, {
    name: category?.name ?? '',
    parent_id: category?.parent_id ?? parentId,
    color: category?.color ?? null,
    budget_cents: category?.budget_cents ?? null,
    notes: category?.notes ?? null,
    archived: category?.archived ?? false,
  })
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) return
  try {
    const body = { ...form, name: form.name.trim() }
    if (editing.value) await api.patch(`categories/${editing.value.id}`, body)
    else
      await api.post('categories', {
        ...body,
        sort_order: app.categories.length,
      })
    dialogVisible.value = false
    await Promise.all([app.loadCategories(), loadFigures()])
    notify.success(editing.value ? 'Category saved' : 'Category added')
  } catch (error) {
    notify.error(error, 'Could not save category')
  }
}

function remove(category: Category) {
  const count = figuresById.value.get(category.id)?.count ?? 0
  const children = app.childrenOf(category.id).length
  const parts = [`Delete “${category.name}”?`]
  if (count) parts.push(`${count} expense(s) will become uncategorised.`)
  if (children) parts.push(`Its ${children} subcategories become top-level categories.`)
  parts.push('Tip: archive it instead to keep history.')
  confirmDelete(parts.join(' '), async () => {
    try {
      await api.del(`categories/${category.id}`)
      await Promise.all([app.loadCategories(), loadFigures()])
      app.touch()
    } catch (error) {
      notify.error(error)
    }
  })
}

async function move(list: Category[], index: number, delta: number) {
  const target = index + delta
  if (target < 0 || target >= list.length) return
  const reordered = [...list]
  const [item] = reordered.splice(index, 1)
  reordered.splice(target, 0, item!)
  try {
    await Promise.all(reordered.map((c, i) => api.patch(`categories/${c.id}`, { sort_order: i })))
    await app.loadCategories()
  } catch (error) {
    notify.error(error)
  }
}

function openExpenses(category: Category) {
  router.push({ path: '/expenses', query: { category: category.id } })
}

watch(() => app.dataVersion, loadFigures)
onMounted(loadFigures)
</script>

<template>
  <div class="toolbar">
    <div class="muted">
      Working budget {{ money(working) }} · allocated to categories {{ money(allocated) }} ·
      <strong :class="{ over: allocated > working }">unallocated {{ money(working - allocated) }}</strong>
    </div>
    <span class="spacer" />
    <label class="row small">
      <ToggleSwitch v-model="showArchived" /> Show archived
    </label>
    <Button label="New category" icon="pi pi-plus" @click="openDialog(null)" />
  </div>

  <div class="card">
    <div class="card-head">
      <span class="muted small">Spending of subcategories rolls up into their parent. Budgets incl. VAT.</span>
      <BudgetLegend />
    </div>
    <div v-if="!tree.length" class="empty">
      <i class="pi pi-tags" />No categories yet. Start with the big blocks: structural work, electrical, plumbing, kitchen…
    </div>
    <div v-for="(node, index) in tree" :key="node.category.id" class="group">
      <div class="cat-row parent" :class="{ archived: node.category.archived }">
        <div class="name">
          <i class="swatch" :style="{ background: node.category.color ?? 'var(--baseline)' }" />
          <a href="#" @click.prevent="openExpenses(node.category)">{{ node.category.name }}</a>
          <span v-if="node.category.archived" class="muted small">(archived)</span>
        </div>
        <div class="num">
          <div>{{ money(figuresById.get(node.category.id)?.forecast ?? 0) }}</div>
          <div class="muted small">of {{ money(figuresById.get(node.category.id)?.budget ?? null) }}</div>
        </div>
        <BudgetBar
          v-if="figuresById.get(node.category.id)"
          v-bind="{
            paid: figuresById.get(node.category.id)!.paid,
            outstanding: figuresById.get(node.category.id)!.outstanding,
            quoted: figuresById.get(node.category.id)!.quoted,
            estimated: figuresById.get(node.category.id)!.estimated,
            budget: figuresById.get(node.category.id)!.budget,
          }"
          :scale="scale"
        />
        <div v-else />
        <HealthBadge :health="figuresById.get(node.category.id)?.health ?? 'none'" />
        <div class="actions">
          <Button v-tooltip.top="'Move up'" icon="pi pi-arrow-up" text rounded size="small" :disabled="index === 0" @click="move(tree.map((n) => n.category), index, -1)" />
          <Button v-tooltip.top="'Move down'" icon="pi pi-arrow-down" text rounded size="small" :disabled="index === tree.length - 1" @click="move(tree.map((n) => n.category), index, 1)" />
          <Button v-tooltip.top="'Add subcategory'" icon="pi pi-plus" text rounded size="small" @click="openDialog(null, node.category.id)" />
          <Button v-tooltip.top="'Edit'" icon="pi pi-pencil" text rounded size="small" @click="openDialog(node.category)" />
          <Button v-tooltip.top="'Delete'" icon="pi pi-trash" text rounded size="small" severity="danger" @click="remove(node.category)" />
        </div>
      </div>
      <div
        v-for="(child, childIndex) in node.children"
        :key="child.id"
        class="cat-row child"
        :class="{ archived: child.archived }"
      >
        <div class="name">
          <i class="swatch" :style="{ background: child.color ?? node.category.color ?? 'var(--baseline)' }" />
          <a href="#" @click.prevent="openExpenses(child)">{{ child.name }}</a>
          <span v-if="child.archived" class="muted small">(archived)</span>
        </div>
        <div class="num">
          <div>{{ money(figuresById.get(child.id)?.forecast ?? 0) }}</div>
          <div v-if="child.budget_cents" class="muted small">of {{ money(child.budget_cents) }}</div>
        </div>
        <BudgetBar
          v-if="figuresById.get(child.id)"
          v-bind="{
            paid: figuresById.get(child.id)!.paid,
            outstanding: figuresById.get(child.id)!.outstanding,
            quoted: figuresById.get(child.id)!.quoted,
            estimated: figuresById.get(child.id)!.estimated,
            budget: figuresById.get(child.id)!.budget,
          }"
          :scale="scale"
          :height="8"
        />
        <div v-else />
        <HealthBadge :health="figuresById.get(child.id)?.health ?? 'none'" />
        <div class="actions">
          <Button icon="pi pi-arrow-up" text rounded size="small" aria-label="Move up" :disabled="childIndex === 0" @click="move(node.children, childIndex, -1)" />
          <Button icon="pi pi-arrow-down" text rounded size="small" aria-label="Move down" :disabled="childIndex === node.children.length - 1" @click="move(node.children, childIndex, 1)" />
          <Button icon="pi pi-pencil" text rounded size="small" aria-label="Edit" @click="openDialog(child)" />
          <Button icon="pi pi-trash" text rounded size="small" severity="danger" aria-label="Delete" @click="remove(child)" />
        </div>
      </div>
    </div>
  </div>

  <Dialog
    v-model:visible="dialogVisible"
    :header="editing ? 'Edit category' : 'New category'"
    modal
    :style="{ width: '460px' }"
  >
    <form id="category-form" class="stack" @submit.prevent="save">
      <div class="field">
        <label for="cat-name">Name</label>
        <InputText id="cat-name" v-model="form.name" autofocus />
      </div>
      <div class="field">
        <label for="cat-parent">Parent category</label>
        <Select
          v-model="form.parent_id"
          input-id="cat-parent"
          :options="parentOptions"
          option-label="name"
          option-value="id"
          show-clear
          :disabled="!canHaveParent"
          placeholder="None (top-level)"
        />
        <span v-if="!canHaveParent" class="hint">This category has subcategories, so it stays top-level.</span>
      </div>
      <div class="field">
        <label for="cat-budget">Budget (incl. VAT)</label>
        <MoneyInput v-model="form.budget_cents" input-id="cat-budget" placeholder="No budget" />
        <span v-if="!form.parent_id" class="hint">Leave empty to use the sum of its subcategory budgets.</span>
      </div>
      <div class="field">
        <label>Colour</label>
        <ColorSwatches v-model="form.color" />
      </div>
      <div class="field">
        <label for="cat-notes">Notes</label>
        <Textarea id="cat-notes" v-model="form.notes" rows="2" auto-resize />
      </div>
      <label v-if="editing" class="row"><Checkbox v-model="form.archived" binary /> Archived (hidden from pickers)</label>
    </form>
    <template #footer>
      <Button label="Cancel" severity="secondary" outlined @click="dialogVisible = false" />
      <Button type="submit" form="category-form" label="Save" icon="pi pi-check" :disabled="!form.name.trim()" />
    </template>
  </Dialog>
</template>

<style scoped>
.group {
  border-top: 1px solid var(--border);
}
.group:first-of-type {
  border-top: none;
}
.cat-row {
  display: grid;
  grid-template-columns: minmax(160px, 1.2fr) 130px minmax(140px, 2fr) 120px auto;
  align-items: center;
  gap: 16px;
  padding: 10px 4px;
}
.cat-row.child {
  padding-left: 28px;
  padding-top: 6px;
  padding-bottom: 6px;
}
.cat-row.archived {
  opacity: 0.55;
}
.name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.name a {
  color: var(--text);
  text-decoration: none;
  font-weight: 600;
}
.child .name a {
  font-weight: 500;
}
.actions {
  display: flex;
  justify-content: flex-end;
}
.over {
  color: var(--status-critical-text);
}
@media (max-width: 900px) {
  .cat-row {
    grid-template-columns: 1fr auto;
  }
  .cat-row > :nth-child(3),
  .cat-row > :nth-child(4) {
    grid-column: 1 / -1;
  }
}
</style>
