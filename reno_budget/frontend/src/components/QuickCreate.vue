<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Popover from 'primevue/popover'
import { nextTick, ref } from 'vue'

/** "+" button that asks for a name and emits it, for adding a room/supplier inline. */
const props = defineProps<{ label: string }>()
const emit = defineEmits<{ create: [name: string] }>()

const popover = ref<InstanceType<typeof Popover> | null>(null)
const name = ref('')
const input = ref<{ $el: HTMLInputElement } | null>(null)

function toggle(event: Event) {
  name.value = ''
  popover.value?.toggle(event)
  nextTick(() => input.value?.$el.focus())
}

function submit() {
  const value = name.value.trim()
  if (!value) return
  emit('create', value)
  popover.value?.hide()
}
</script>

<template>
  <Button
    v-tooltip.top="`New ${props.label}`"
    icon="pi pi-plus"
    severity="secondary"
    outlined
    :aria-label="`New ${props.label}`"
    @click="toggle"
  />
  <Popover ref="popover">
    <form class="row" @submit.prevent="submit">
      <InputText ref="input" v-model="name" :placeholder="`New ${props.label} name`" />
      <Button type="submit" label="Add" :disabled="!name.trim()" />
    </form>
  </Popover>
</template>
