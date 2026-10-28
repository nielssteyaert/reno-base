<script setup lang="ts">
import Button from 'primevue/button'
import Select from 'primevue/select'
import { ref } from 'vue'
import { api, apiUrl } from '@/api'
import { useConfirmDelete, useNotify } from '@/composables'
import { ATTACHMENT_KIND_OPTIONS, dateTime, fileSize } from '@/format'
import type { Attachment, AttachmentKind, ExpenseDetail } from '@/types'

const props = defineProps<{ expense: ExpenseDetail }>()
const emit = defineEmits<{ changed: [] }>()
const notify = useNotify()
const confirmDelete = useConfirmDelete()

const kind = ref<AttachmentKind>('invoice')
const uploading = ref(false)
const dragging = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const isImage = (a: Attachment) => a.mime_type.startsWith('image/') && a.mime_type !== 'image/svg+xml'
const iconFor = (a: Attachment) =>
  a.mime_type === 'application/pdf'
    ? 'pi pi-file-pdf'
    : a.mime_type.includes('sheet') || a.mime_type.includes('excel')
      ? 'pi pi-file-excel'
      : a.mime_type.includes('word')
        ? 'pi pi-file-word'
        : 'pi pi-file'

async function upload(files: FileList | File[] | null) {
  if (!files || files.length === 0) return
  const form = new FormData()
  for (const file of Array.from(files)) form.append('files', file)
  form.append('kind', kind.value)
  uploading.value = true
  try {
    await api.upload(`expenses/${props.expense.id}/attachments`, form)
    notify.success(files.length === 1 ? 'File uploaded' : `${files.length} files uploaded`)
    emit('changed')
  } catch (error) {
    notify.error(error, 'Upload failed')
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

function onDrop(event: DragEvent) {
  dragging.value = false
  upload(event.dataTransfer?.files ?? null)
}

async function changeKind(attachment: Attachment, value: AttachmentKind) {
  try {
    await api.patch(`attachments/${attachment.id}`, { kind: value })
    emit('changed')
  } catch (error) {
    notify.error(error)
  }
}

function remove(attachment: Attachment) {
  confirmDelete(`Delete “${attachment.original_name}”?`, async () => {
    try {
      await api.del(`attachments/${attachment.id}`)
      emit('changed')
    } catch (error) {
      notify.error(error)
    }
  })
}
</script>

<template>
  <div class="stack">
    <div
      class="dropzone"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <i class="pi pi-cloud-upload" />
      <div>Drop quotes, invoices or photos here (max 25 MB each)</div>
      <div class="row">
        <Select
          v-model="kind"
          :options="ATTACHMENT_KIND_OPTIONS"
          option-label="label"
          option-value="value"
          aria-label="File type"
          size="small"
        />
        <Button label="Choose files" icon="pi pi-paperclip" size="small" :loading="uploading" @click="fileInput?.click()" />
      </div>
      <input
        ref="fileInput"
        type="file"
        multiple
        hidden
        @change="upload(($event.target as HTMLInputElement).files)"
      />
    </div>

    <div v-if="props.expense.attachments.length === 0" class="empty small">No files attached yet.</div>
    <ul v-else class="files">
      <li v-for="attachment in props.expense.attachments" :key="attachment.id" class="card file">
        <a class="thumb" :href="apiUrl(`attachments/${attachment.id}/file`)" target="_blank" rel="noopener">
          <img v-if="isImage(attachment)" :src="apiUrl(`attachments/${attachment.id}/file`)" :alt="attachment.original_name" loading="lazy" />
          <i v-else :class="iconFor(attachment)" />
        </a>
        <div class="meta">
          <a :href="apiUrl(`attachments/${attachment.id}/file`)" target="_blank" rel="noopener" class="name">
            {{ attachment.original_name }}
          </a>
          <div class="muted small">
            {{ fileSize(attachment.size_bytes) }} · {{ dateTime(attachment.uploaded_at) }}
            <template v-if="attachment.uploaded_by"> · {{ attachment.uploaded_by }}</template>
          </div>
        </div>
        <Select
          :model-value="attachment.kind"
          :options="ATTACHMENT_KIND_OPTIONS"
          option-label="label"
          option-value="value"
          size="small"
          aria-label="File type"
          @update:model-value="changeKind(attachment, $event)"
        />
        <a :href="apiUrl(`attachments/${attachment.id}/file`, { download: true })" download>
          <Button icon="pi pi-download" text rounded aria-label="Download" />
        </a>
        <Button icon="pi pi-trash" text rounded severity="danger" aria-label="Delete file" @click="remove(attachment)" />
      </li>
    </ul>
  </div>
</template>

<style scoped>
.dropzone {
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--text-2);
  text-align: center;
}
.dropzone.dragging {
  border-color: var(--p-primary-color);
  background: var(--nav-active);
}
.dropzone > .pi {
  font-size: 24px;
}
.files {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.file {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
}
.thumb {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  background: var(--surface-sunken);
  display: grid;
  place-items: center;
  overflow: hidden;
  flex: none;
  color: var(--text-2);
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb .pi {
  font-size: 22px;
}
.meta {
  flex: 1;
  min-width: 0;
}
.name {
  display: block;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: none;
}
</style>
