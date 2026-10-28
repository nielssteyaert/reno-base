<script setup lang="ts">
/** Pick a colour from the fixed categorical palette (or none). */
const color = defineModel<string | null>({ default: null })

const PALETTE = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
</script>

<template>
  <div class="swatches" role="radiogroup" aria-label="Colour">
    <button
      type="button"
      class="swatch-btn none"
      :class="{ selected: !color }"
      aria-label="No colour"
      @click="color = null"
    >
      <i class="pi pi-ban" />
    </button>
    <button
      v-for="hex in PALETTE"
      :key="hex"
      type="button"
      class="swatch-btn"
      :class="{ selected: color === hex }"
      :style="{ background: hex }"
      :aria-label="hex"
      @click="color = hex"
    />
  </div>
</template>

<style scoped>
.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.swatch-btn {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0;
  outline-offset: 2px;
}
.swatch-btn.selected {
  outline: 2px solid var(--text);
}
.swatch-btn.none {
  background: var(--surface-sunken);
  color: var(--text-muted);
  display: grid;
  place-items: center;
}
</style>
