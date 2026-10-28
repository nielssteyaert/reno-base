<script setup lang="ts">
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import ProgressSpinner from 'primevue/progressspinner'
import SelectButton from 'primevue/selectbutton'
import Toast from 'primevue/toast'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import ExpenseDrawer from './components/ExpenseDrawer.vue'
import { useAppStore } from './stores/app'
import { applyTheme, storedTheme, watchSystemTheme, type ThemeChoice } from './theme'

const app = useAppStore()
const route = useRoute()
const menuOpen = ref(false)
const loadError = ref<string | null>(null)
const theme = ref<ThemeChoice>(storedTheme())

const nav = [
  {
    title: 'Overview',
    links: [
      { to: '/', icon: 'pi pi-home', label: 'Dashboard' },
      { to: '/expenses', icon: 'pi pi-receipt', label: 'Expenses' },
      { to: '/timeline', icon: 'pi pi-calendar', label: 'Timeline' },
      { to: '/reports', icon: 'pi pi-chart-bar', label: 'Reports' },
    ],
  },
  {
    title: 'Manage',
    links: [
      { to: '/categories', icon: 'pi pi-tags', label: 'Categories' },
      { to: '/rooms', icon: 'pi pi-building', label: 'Rooms' },
      { to: '/suppliers', icon: 'pi pi-users', label: 'Suppliers' },
    ],
  },
  {
    title: 'Data',
    links: [
      { to: '/import', icon: 'pi pi-upload', label: 'Import' },
      { to: '/backups', icon: 'pi pi-database', label: 'Backups' },
      { to: '/history', icon: 'pi pi-history', label: 'History' },
      { to: '/settings', icon: 'pi pi-cog', label: 'Settings' },
    ],
  },
]

const themeOptions = [
  { value: 'auto', icon: 'pi pi-desktop', label: 'Follow Home Assistant' },
  { value: 'light', icon: 'pi pi-sun', label: 'Light' },
  { value: 'dark', icon: 'pi pi-moon', label: 'Dark' },
]

const title = computed(() => (route.meta.title as string) ?? '')

function isActive(to: string) {
  return to !== '/' && route.path.startsWith(to)
}

watch(theme, (value) => applyTheme(value))
watch(
  () => route.fullPath,
  () => (menuOpen.value = false),
)

onMounted(async () => {
  watchSystemTheme(() => theme.value)
  try {
    await app.loadAll()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : String(error)
  }
})
</script>

<template>
  <Toast position="bottom-right" />
  <ConfirmDialog />
  <div class="shell">
    <aside class="sidebar" :class="{ open: menuOpen }">
      <div class="brand"><i class="pi pi-home" />Renovation Budget</div>
      <nav>
        <div v-for="group in nav" :key="group.title" class="nav-group">
          <div class="nav-group-title">{{ group.title }}</div>
          <RouterLink
            v-for="link in group.links"
            :key="link.to"
            :to="link.to"
            class="nav-link"
            :class="{ active: isActive(link.to) }"
          >
            <i :class="link.icon" />{{ link.label }}
          </RouterLink>
        </div>
      </nav>
    </aside>
    <div class="main">
      <header class="topbar">
        <Button
          class="menu-toggle"
          icon="pi pi-bars"
          text
          rounded
          aria-label="Menu"
          @click="menuOpen = !menuOpen"
        />
        <div>
          <h1>{{ title }}</h1>
          <div v-if="app.settings" class="project">{{ app.settings.project_name }}</div>
        </div>
        <div class="spacer" />
        <SelectButton
          v-model="theme"
          :options="themeOptions"
          option-value="value"
          data-key="value"
          :allow-empty="false"
          size="small"
          aria-label="Colour theme"
        >
          <template #option="{ option }">
            <i v-tooltip.bottom="option.label" :class="option.icon" />
          </template>
        </SelectButton>
      </header>
      <main class="content">
        <div v-if="loadError" class="card empty">
          <i class="pi pi-exclamation-circle" />
          Could not reach the Renovation Budget backend: {{ loadError }}
        </div>
        <div v-else-if="!app.loaded" class="empty"><ProgressSpinner style="width: 40px; height: 40px" /></div>
        <RouterView v-else />
      </main>
    </div>
  </div>
  <ExpenseDrawer v-if="app.loaded" />
</template>
