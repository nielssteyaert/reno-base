import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Expense } from '@/types'

/** Opens the global expense drawer from anywhere (expense list, dashboard, reports). */
export const useDrawerStore = defineStore('drawer', () => {
  const visible = ref(false)
  const expenseId = ref<number | null>(null)
  const defaults = ref<Partial<Expense>>({})

  function open(id: number) {
    expenseId.value = id
    defaults.value = {}
    visible.value = true
  }

  function create(initial: Partial<Expense> = {}) {
    expenseId.value = null
    defaults.value = initial
    visible.value = true
  }

  function close() {
    visible.value = false
  }

  return { visible, expenseId, defaults, open, create, close }
})
