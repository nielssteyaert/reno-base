import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api'
import { configureFormatting } from '@/format'
import type { Category, Milestone, Room, Settings, Supplier } from '@/types'

/** Reference data used across views: settings, categories, rooms, suppliers and milestones. */
export const useAppStore = defineStore('app', () => {
  const settings = ref<Settings | null>(null)
  const categories = ref<Category[]>([])
  const rooms = ref<Room[]>([])
  const suppliers = ref<Supplier[]>([])
  const milestones = ref<Milestone[]>([])
  const user = ref<string>('')
  const loaded = ref(false)
  // Bumped whenever expenses change, so views showing totals know to reload.
  const dataVersion = ref(0)

  async function loadSettings() {
    settings.value = await api.get<Settings>('settings')
    configureFormatting(settings.value.locale, settings.value.currency)
  }
  async function loadCategories() {
    categories.value = await api.get<Category[]>('categories')
  }
  async function loadRooms() {
    rooms.value = await api.get<Room[]>('rooms')
  }
  async function loadSuppliers() {
    suppliers.value = await api.get<Supplier[]>('suppliers')
  }
  async function loadMilestones() {
    milestones.value = await api.get<Milestone[]>('milestones')
  }

  async function loadAll() {
    await Promise.all([
      loadSettings(),
      loadCategories(),
      loadRooms(),
      loadSuppliers(),
      loadMilestones(),
      api.get<{ user: string }>('me').then((me) => (user.value = me.user)),
    ])
    loaded.value = true
  }

  function touch() {
    dataVersion.value++
  }

  const categoryById = computed(() => new Map(categories.value.map((c) => [c.id, c])))
  const roomById = computed(() => new Map(rooms.value.map((r) => [r.id, r])))
  const supplierById = computed(() => new Map(suppliers.value.map((s) => [s.id, s])))
  const milestoneById = computed(() => new Map(milestones.value.map((m) => [m.id, m])))

  function categoryPath(id: number | null): string {
    if (id === null) return ''
    const category = categoryById.value.get(id)
    if (!category) return ''
    const parent = category.parent_id ? categoryById.value.get(category.parent_id) : null
    return parent ? `${parent.name} › ${category.name}` : category.name
  }

  const topCategories = computed(() => categories.value.filter((c) => c.parent_id === null))

  function childrenOf(id: number): Category[] {
    return categories.value.filter((c) => c.parent_id === id)
  }

  /** Flat option list for selects: parents followed by their children, archived ones hidden. */
  function categoryOptions(includeId: number | null = null) {
    const options: { value: number; label: string; depth: number }[] = []
    for (const parent of topCategories.value) {
      if (!parent.archived || parent.id === includeId)
        options.push({ value: parent.id, label: parent.name, depth: 0 })
      for (const child of childrenOf(parent.id)) {
        if (!child.archived || child.id === includeId)
          options.push({ value: child.id, label: `${parent.name} › ${child.name}`, depth: 1 })
      }
    }
    return options
  }

  const activeRooms = computed(() => rooms.value.filter((r) => !r.archived))
  const activeSuppliers = computed(() => suppliers.value.filter((s) => !s.archived))

  return {
    settings,
    categories,
    rooms,
    suppliers,
    milestones,
    user,
    loaded,
    dataVersion,
    loadAll,
    loadSettings,
    loadCategories,
    loadRooms,
    loadSuppliers,
    loadMilestones,
    touch,
    categoryById,
    roomById,
    supplierById,
    milestoneById,
    categoryPath,
    topCategories,
    childrenOf,
    categoryOptions,
    activeRooms,
    activeSuppliers,
  }
})
