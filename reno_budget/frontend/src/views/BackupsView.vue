<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { onMounted, ref } from 'vue'
import { api, apiUrl } from '@/api'
import { useConfirmDelete, useNotify } from '@/composables'
import { dateTime, fileSize } from '@/format'
import { useAppStore } from '@/stores/app'
import type { BackupInfo } from '@/types'

const app = useAppStore()
const notify = useNotify()
const confirm = useConfirm()
const confirmDelete = useConfirmDelete()

const backups = ref<BackupInfo[]>([])
const loading = ref(false)
const creating = ref(false)
const restoring = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const REASONS: Record<string, { label: string; severity: string }> = {
  manual: { label: 'Manual', severity: 'info' },
  auto: { label: 'Nightly', severity: 'secondary' },
  'pre-restore': { label: 'Before restore', severity: 'warn' },
}

async function load() {
  loading.value = true
  try {
    backups.value = await api.get<BackupInfo[]>('backups')
  } catch (error) {
    notify.error(error)
  } finally {
    loading.value = false
  }
}

async function create() {
  creating.value = true
  try {
    await api.post('backups')
    notify.success('Backup created')
    await load()
  } catch (error) {
    notify.error(error, 'Backup failed')
  } finally {
    creating.value = false
  }
}

async function afterRestore(safety: string) {
  await app.loadAll()
  app.touch()
  await load()
  notify.success('Backup restored', `Your previous data was saved as ${safety}`)
}

function restore(backup: BackupInfo) {
  confirm.require({
    header: 'Restore this backup?',
    message: `All current data and files will be replaced by the backup from ${dateTime(backup.created_at)}. A safety backup of the current state is made first.`,
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: 'Cancel', severity: 'secondary', outlined: true },
    acceptProps: { label: 'Restore', severity: 'danger' },
    accept: async () => {
      restoring.value = true
      try {
        const result = await api.post<{ safety_backup: string }>(`backups/${backup.name}/restore`)
        await afterRestore(result.safety_backup)
      } catch (error) {
        notify.error(error, 'Restore failed')
      } finally {
        restoring.value = false
      }
    },
  })
}

function restoreFromFile(files: FileList | null) {
  const file = files?.[0]
  if (!file) return
  confirm.require({
    header: 'Restore from file?',
    message: `All current data will be replaced by “${file.name}”. A safety backup is made first.`,
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: 'Cancel', severity: 'secondary', outlined: true },
    acceptProps: { label: 'Restore', severity: 'danger' },
    accept: async () => {
      restoring.value = true
      const form = new FormData()
      form.append('file', file)
      try {
        const result = await api.upload<{ safety_backup: string }>('backups/upload-restore', form)
        await afterRestore(result.safety_backup)
      } catch (error) {
        notify.error(error, 'Restore failed')
      } finally {
        restoring.value = false
        if (fileInput.value) fileInput.value.value = ''
      }
    },
    reject: () => {
      if (fileInput.value) fileInput.value.value = ''
    },
  })
}

function remove(backup: BackupInfo) {
  confirmDelete(`Delete backup ${backup.name}?`, async () => {
    try {
      await api.del(`backups/${backup.name}`)
      await load()
    } catch (error) {
      notify.error(error)
    }
  })
}

onMounted(load)
</script>

<template>
  <div class="stack">
    <Message severity="secondary" :closable="false">
      A backup is a zip with the database and every attached file. Nightly backups run at 03:00 when enabled in
      the app's configuration. Home Assistant's own backups include this app's data too.
    </Message>

    <div class="toolbar" style="margin: 0">
      <Button label="Back up now" icon="pi pi-database" :loading="creating" @click="create" />
      <Button label="Restore from file…" icon="pi pi-upload" severity="secondary" outlined :loading="restoring" @click="fileInput?.click()" />
      <input ref="fileInput" type="file" accept=".zip,application/zip" hidden @change="restoreFromFile(($event.target as HTMLInputElement).files)" />
    </div>

    <div class="card" style="padding: 0; overflow: hidden">
      <DataTable :value="backups" :loading="loading" data-key="name" size="small">
        <template #empty><div class="empty"><i class="pi pi-database" />No backups yet.</div></template>
        <Column header="Created">
          <template #body="{ data }">{{ dateTime(data.created_at) }}</template>
        </Column>
        <Column header="Type">
          <template #body="{ data }">
            <Tag :value="REASONS[data.reason]?.label ?? data.reason" :severity="REASONS[data.reason]?.severity ?? 'secondary'" />
          </template>
        </Column>
        <Column header="Size" class="num"><template #body="{ data }">{{ fileSize(data.size_bytes) }}</template></Column>
        <Column header="Files" class="num"><template #body="{ data }">{{ data.attachments ?? '—' }}</template></Column>
        <Column header="Version"><template #body="{ data }">{{ data.app_version }}</template></Column>
        <Column style="width: 150px">
          <template #body="{ data }">
            <div class="row" style="justify-content: flex-end">
              <a :href="apiUrl(`backups/${data.name}`)" download>
                <Button v-tooltip.top="'Download'" icon="pi pi-download" text rounded size="small" aria-label="Download" />
              </a>
              <Button v-tooltip.top="'Restore'" icon="pi pi-replay" text rounded size="small" :disabled="restoring" @click="restore(data)" />
              <Button v-tooltip.top="'Delete'" icon="pi pi-trash" text rounded size="small" severity="danger" @click="remove(data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>
