import type { Health, MilestoneStatus, PaymentMethod, Status } from './types'

let locale = 'nl-BE'
let currency = 'EUR'
let moneyFormat = new Intl.NumberFormat(locale, { style: 'currency', currency })
let compactFormat = new Intl.NumberFormat(locale, { style: 'currency', currency, notation: 'compact' })

export function configureFormatting(newLocale: string, newCurrency: string) {
  locale = newLocale || 'nl-BE'
  currency = newCurrency || 'EUR'
  try {
    moneyFormat = new Intl.NumberFormat(locale, { style: 'currency', currency })
    compactFormat = new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      notation: 'compact',
      maximumFractionDigits: 1,
    })
  } catch {
    moneyFormat = new Intl.NumberFormat('nl-BE', { style: 'currency', currency: 'EUR' })
  }
}

export const currentLocale = () => locale
export const currentCurrency = () => currency

export function money(cents: number | null | undefined): string {
  if (cents === null || cents === undefined) return '—'
  return moneyFormat.format(cents / 100)
}

export function moneyCompact(cents: number | null | undefined): string {
  if (cents === null || cents === undefined) return '—'
  return compactFormat.format(cents / 100)
}

export function pct(ratio: number | null | undefined, digits = 0): string {
  if (ratio === null || ratio === undefined) return '—'
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: digits,
  }).format(ratio)
}

export function vatRate(rate: number): string {
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(rate)}%`
}

function dateParts(iso: string): [number, number, number] {
  const [y = 1970, m = 1, d = 1] = iso.slice(0, 10).split('-').map(Number)
  return [y, m, d]
}

/** "2026-03-01" → localised short date. Dates are plain calendar dates, not instants. */
export function day(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [y, m, d] = dateParts(iso)
  return new Date(y, m - 1, d).toLocaleDateString(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function monthLabel(month: string): string {
  const [y, m] = dateParts(`${month}-01`)
  return new Date(y, m - 1, 1).toLocaleDateString(locale, { month: 'short', year: '2-digit' })
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** Date → "YYYY-MM-DD" in local time (what the API expects). */
export function toIsoDate(date: Date | null | undefined): string | null {
  if (!date) return null
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function fromIsoDate(iso: string | null | undefined): Date | null {
  if (!iso) return null
  const [y, m, d] = dateParts(iso)
  return new Date(y, m - 1, d)
}

export const todayIso = () => toIsoDate(new Date()) as string

export const STATUS_LABELS: Record<Status, string> = {
  estimate: 'Estimate',
  quote: 'Quote',
  ordered: 'Ordered',
  invoiced: 'Invoiced',
  paid: 'Paid',
}

export const STATUS_ORDER: Status[] = ['estimate', 'quote', 'ordered', 'invoiced', 'paid']

export const STAGE_OPTIONS = (['estimate', 'quote', 'ordered', 'invoiced'] as const).map((value) => ({
  value,
  label: STATUS_LABELS[value],
}))

export const STATUS_OPTIONS = STATUS_ORDER.map((value) => ({ value, label: STATUS_LABELS[value] }))

export const PAYMENT_STATUS_LABELS = { unpaid: 'Unpaid', partial: 'Partly paid', paid: 'Paid' }

export const METHOD_LABELS: Record<PaymentMethod, string> = {
  bank_transfer: 'Bank transfer',
  card: 'Card',
  cash: 'Cash',
  other: 'Other',
}

export const METHOD_OPTIONS = Object.entries(METHOD_LABELS).map(([value, label]) => ({ value, label }))

export const ATTACHMENT_KIND_OPTIONS = [
  { value: 'quote', label: 'Quote' },
  { value: 'invoice', label: 'Invoice' },
  { value: 'photo', label: 'Photo' },
  { value: 'other', label: 'Other' },
]

export const MILESTONE_LABELS: Record<MilestoneStatus, string> = {
  planned: 'Planned',
  in_progress: 'In progress',
  done: 'Done',
  late: 'Late',
}

export const HEALTH_LABELS: Record<Health, string> = {
  none: 'No budget',
  ok: 'On track',
  warning: 'Near budget',
  over: 'Over budget',
}

export const HEALTH_ICONS: Record<Health, string> = {
  none: 'pi pi-minus-circle',
  ok: 'pi pi-check-circle',
  warning: 'pi pi-exclamation-triangle',
  over: 'pi pi-times-circle',
}
