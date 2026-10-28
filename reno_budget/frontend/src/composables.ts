import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

export function useNotify() {
  const toast = useToast()
  return {
    success(summary: string, detail?: string) {
      toast.add({ severity: 'success', summary, detail, life: 3000 })
    },
    error(error: unknown, summary = 'Something went wrong') {
      const detail = error instanceof Error ? error.message : String(error)
      toast.add({ severity: 'error', summary, detail, life: 6000 })
    },
  }
}

export function useConfirmDelete() {
  const confirm = useConfirm()
  return (message: string, onAccept: () => void | Promise<void>, header = 'Delete?') =>
    confirm.require({
      header,
      message,
      icon: 'pi pi-exclamation-triangle',
      rejectProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      acceptProps: { label: 'Delete', severity: 'danger' },
      accept: onAccept,
    })
}
