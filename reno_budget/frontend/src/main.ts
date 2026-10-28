import { definePreset } from '@primeuix/themes'
import Aura from '@primeuix/themes/aura'
import { createPinia } from 'pinia'
import 'primeicons/primeicons.css'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import Tooltip from 'primevue/tooltip'
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import './styles.css'
import { applyTheme, storedTheme } from './theme'

const Preset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '{sky.50}',
      100: '{sky.100}',
      200: '{sky.200}',
      300: '{sky.300}',
      400: '{sky.400}',
      500: '{sky.500}',
      600: '{sky.600}',
      700: '{sky.700}',
      800: '{sky.800}',
      900: '{sky.900}',
      950: '{sky.950}',
    },
  },
})

applyTheme(storedTheme())

createApp(App)
  .use(createPinia())
  .use(router)
  .use(PrimeVue, {
    theme: { preset: Preset, options: { darkModeSelector: '.app-dark' } },
    locale: { firstDayOfWeek: 1, dateFormat: 'dd/mm/yy' },
  })
  .use(ToastService)
  .use(ConfirmationService)
  .directive('tooltip', Tooltip)
  .mount('#app')
