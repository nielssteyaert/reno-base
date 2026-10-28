import { createRouter, createWebHashHistory } from 'vue-router'

// Hash history: Home Assistant ingress only routes the app's base path to us.
export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('./views/DashboardView.vue'), meta: { title: 'Dashboard' } },
    { path: '/expenses', name: 'expenses', component: () => import('./views/ExpensesView.vue'), meta: { title: 'Expenses' } },
    { path: '/timeline', name: 'timeline', component: () => import('./views/TimelineView.vue'), meta: { title: 'Timeline' } },
    { path: '/reports/:tab?', name: 'reports', component: () => import('./views/ReportsView.vue'), meta: { title: 'Reports' } },
    { path: '/categories', name: 'categories', component: () => import('./views/CategoriesView.vue'), meta: { title: 'Categories' } },
    { path: '/rooms', name: 'rooms', component: () => import('./views/RoomsView.vue'), meta: { title: 'Rooms' } },
    { path: '/suppliers', name: 'suppliers', component: () => import('./views/SuppliersView.vue'), meta: { title: 'Suppliers' } },
    { path: '/import', name: 'import', component: () => import('./views/ImportView.vue'), meta: { title: 'Import' } },
    { path: '/backups', name: 'backups', component: () => import('./views/BackupsView.vue'), meta: { title: 'Backups' } },
    { path: '/history', name: 'history', component: () => import('./views/HistoryView.vue'), meta: { title: 'History' } },
    { path: '/settings', name: 'settings', component: () => import('./views/SettingsView.vue'), meta: { title: 'Settings' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
