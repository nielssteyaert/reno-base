import { onBeforeUnmount, ref } from 'vue'

/** Chart colours read from the CSS tokens; refreshed when the theme changes. */
export function useChartTheme() {
  const read = () => {
    const css = getComputedStyle(document.documentElement)
    const v = (name: string) => css.getPropertyValue(name).trim()
    return {
      series1: v('--series-1'),
      series2: v('--series-2'),
      ink: v('--budget-marker'),
      text: v('--text-2'),
      muted: v('--text-muted'),
      grid: v('--grid'),
      baseline: v('--baseline'),
      surface: v('--surface'),
    }
  }
  const colors = ref(read())
  const update = () => (colors.value = read())
  window.addEventListener('reno-theme', update)
  onBeforeUnmount(() => window.removeEventListener('reno-theme', update))
  return colors
}
