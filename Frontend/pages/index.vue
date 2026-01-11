<template>
  <div class="min-h-screen bg-white">
    <!-- Header -->
    <header class="border-b border-gray-200">
      <div class="mx-auto max-w-6xl px-4 py-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-3">
          <div>
            <div class="font-semibold leading-5">PhysioLens DEMO</div>
            <div class="text-sm text-gray-500">Recovery factors analysis dashboard</div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <!-- Demo Scenario Selector -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-600">Demo Scenarios</span>

            <div class="flex rounded-lg border border-gray-200 p-0.5">
              <button
                v-for="s in scenarios"
                :key="s.key"
                @click="selectScenario(s)"
                class="px-3 py-1.5 text-sm rounded-md transition"
                :class="
                  activeScenario.key === s.key
                    ? 'bg-black text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                "
              >
                {{ s.label }}
              </button>
            </div>
          </div>

          <div class="flex flex-col space-y-2">
            <div class="flex items-center gap-2">
              <label class="text-sm text-gray-600">Window</label>
              <input
                v-model.number="windowDays"
                type="number"
                min="7"
                max="365"
                class="w-24 rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-black/10"
              />
            </div>
          </div>


          <button
            @click="refreshAll"
            class="rounded-lg bg-black px-4 py-2 text-sm text-white hover:bg-black/90"
          >
            Refresh
          </button>
        </div>
      </div>
    </header>

    <!-- Body -->
    <main class="mx-auto max-w-6xl px-4 py-6">
      <div class="flex flex-row mb-4 space-x-2 items-center">
        <div class="h-12 w-12 rounded-full border border-gray-200 grid place-items-center overflow-hidden">
          <img src="/images/me.jpg" class="w-full h-full object-cover" />
        </div>
        <text class="font-semibold text-md">
          Collin Brennan's analysis
        </text>
      </div>

      <div v-if="pending" class="text-sm text-gray-600">Loading…</div>

      <div
        v-else-if="error"
        class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
      >
        {{ error }}
      </div>

      <!-- Insufficient Data Warning -->
      <div v-else-if="hasLoadedData && lastLoadedWindow !== null && lastLoadedWindow < 30" class="space-y-4">
        <div class="rounded-2xl border-2 border-amber-200 bg-amber-50 p-6 text-center">
          <div class="mx-auto w-16 h-16 rounded-full bg-amber-100 flex items-center justify-center mb-4">
            <svg class="w-8 h-8 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 class="text-xl font-semibold text-amber-900 mb-2">Insufficient Data</h2>
          <p class="text-sm text-amber-800 max-w-md mx-auto">
            Analysis requires at least 30 days of data to provide meaningful insights and accurate recovery factor patterns. 
            Current window: <span class="font-semibold">{{ windowDays }} days</span>.
          </p>
          <p class="text-xs text-amber-700 mt-3">
            Please adjust the window to 30 days or more using the controls above.
          </p>
        </div>

        <!-- Blurred/Disabled Preview -->
        <div class="relative pointer-events-none select-none">
          <div class="absolute inset-0 bg-white/60 backdrop-blur-sm z-10 rounded-2xl"></div>
          <section class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 opacity-40">
            <div class="rounded-xl border border-gray-200 p-4 h-24 bg-gray-50"></div>
            <div class="rounded-xl border border-gray-200 p-4 h-24 bg-gray-50"></div>
            <div class="rounded-xl border border-gray-200 p-4 h-24 bg-gray-50"></div>
            <div class="rounded-xl border border-gray-200 p-4 h-24 bg-gray-50"></div>
          </section>
        </div>
      </div>

      <div v-else class="space-y-4">
        <section class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="Recovery Score(avg)"
            :value="kpi.recoveryAvg"
            :sub="`std: ${kpi.recoveryStd}`"
            tooltip="Average recovery across the selected window, computed from your daily recovery values."
          />

          <KpiCard
            label="Primary associated factor"
            :value="(summary?.dominant_key ?? '—')"
            :sub="summary?.stable ? 'stable window' : 'dip attribution'"
            :capitalize="true"
            tooltip="The factor that explains the largest share of recovery dips in this window (association, not causation)."
          />

          <KpiCard
            label="Recovery dips"
            :value="String(summary?.meta?.dip_count ?? 0)"
            :sub="`${summary?.meta?.large_dip_count ?? 0} large • ${summary?.meta?.persistent_dip_count ?? 0} persistent`"
            tooltip="A dip is a day where recovery falls meaningfully below your personal baseline. Large and persistent are tracked separately."
          />

          <KpiCard
            label="Signal strength"
            :value="(summary?.insight.signal_strength ?? '—')"
            :sub="summary?.stable
              ? 'no dominant factor detected in this window'
              : 'association strength based on consistency, magnitude, and data sufficiency'"
            :tooltip="`Signal strength is ${(summary?.insight.signal_strength ?? '—')}. It reflects how consistently and strongly this pattern appears in the selected window and does not imply causation.`"
          />
        </section>


        <!-- Main Row -->
        <section class="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <!-- Insight -->
          <div class="rounded-2xl border-2 border-gray-200 p-5 lg:col-span-2">
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="text-sm text-gray-500 font-semibold">Insight</div>
                <h1 class="mt-1 text-xl font-semibold tracking-tight">
                  {{ summary?.insight.title }}
                </h1>
              </div>
              <div>
                <text class="text-xs text-gray-500 font-medium">
                Association value signal strength:
                </text>
                <span
                  class="inline-flex items-center rounded-lg px-3 py-1 text-xs"
                  :class="signal_strengthPillClass"
                >
                  {{ summary?.insight.signal_strength }} 
                </span>
              </div>
            </div>

            <p class="mt-3 text-sm leading-6 text-gray-700">
              {{ summary?.insight.body }}
            </p>

            <div class="mt-4 flex flex-wrap gap-2 text-xs">
              <span 
                class="rounded-lg border border-gray-200 px-3 py-1 text-gray-700 relative group cursor-pointer hover:bg-gray-100"
              >
                stability: <span class="font-medium">{{ summary?.stable ? 'stable' : 'unstable' }}</span>
                <span 
                class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-lg border border-gray-200 
                bg-white px-3 py-2 text-xs text-gray-700 shadow-lg opacity-0 invisible group-hover:opacity-100 
                group-hover:visible transition-all duration-200 pointer-events-none z-10"
                >
                  Indicates whether recovery patterns show consistent stability or notable fluctuations during this window.
                </span>
              </span>

              <span 
                class="rounded-lg border border-gray-200 px-3 py-1 text-gray-700 relative group cursor-pointer hover:bg-gray-100"
              >
                window: <span class="font-medium">{{ summary?.days_window }} days</span>
                <span 
                class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-lg border border-gray-200 
                bg-white px-3 py-2 text-xs text-gray-700 shadow-lg opacity-0 invisible group-hover:opacity-100 
                group-hover:visible transition-all duration-200 pointer-events-none z-10"
                >
                  The number of days analyzed in this report. Larger windows provide more data but may miss recent trends.
                </span>
              </span>

              <span 
                class="rounded-lg border border-gray-200 px-3 py-1 text-gray-700 relative group cursor-pointer hover:bg-gray-100"
              >
                lag: <span class="font-medium">{{ summary?.meta?.pareto?.max_lag_days ?? '-' }}</span>
                <span 
                class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-lg border border-gray-200 
                bg-white px-3 py-2 text-xs text-gray-700 shadow-lg opacity-0 invisible group-hover:opacity-100 
                group-hover:visible transition-all duration-200 pointer-events-none z-10"
                >
                  The typical delay (in days) between an abnormal factor value and its associated recovery dip. Shows temporal relationship patterns.
                </span>
              </span>

              <span 
                class="rounded-lg border border-gray-200 px-3 py-1 text-gray-700 relative group cursor-pointer hover:bg-gray-100"
              >
                abnormal z: <span class="font-medium">{{ summary?.meta?.pareto?.abnormal_abs_z ?? '-' }}</span>
                <span 
                class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-lg border border-gray-200 
                bg-white px-3 py-2 text-xs text-gray-700 shadow-lg opacity-0 invisible group-hover:opacity-100 
                group-hover:visible transition-all duration-200 pointer-events-none z-10"
                >
                  Statistical measure (z-score) showing how far abnormal values deviate from your personal baseline. Higher values indicate stronger deviations.
                </span>
              </span>
            </div>
          </div>

          <!-- Factors -->
          <div class="rounded-2xl border-2 border-gray-200 p-5">
            <div>
              <div class="text-sm text-gray-500 font-semibold">Factors</div>
              <div class="text-sm text-gray-700">Occurence of association during recovery dips by factor.</div>
            </div>

            <div class="mt-4 space-y-3">
              <div v-for="d in (summary?.factors ?? [])" :key="d.key" class="space-y-1">
                <div class="flex items-center justify-between">
                  <div class="text-sm font-medium capitalize">{{ d.key }}</div>
                  <div class="text-sm tabular-nums">{{ d.percent.toFixed(0) }}%</div>
                </div>
                <div class="h-2 w-full rounded-full bg-gray-100">
                  <div class="h-2 rounded-full bg-black" :style="{ width: `${Math.min(100, d.percent)}%` }" />
                </div>
                <div class="flex justify-between text-xs text-gray-500">
                  <span>occurences: {{ d.occurrences }}</span>
                  <span>avg z: {{ d.avg_abs_z.toFixed(2) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Chart + Drilldown -->
          <div class="rounded-2xl border-2 border-gray-200 p-5 lg:col-span-3">
            <div class="flex items-start justify-between gap-4">
              <div>
                <div class="text-sm text-gray-500 font-semibold">Recovery timeline</div>
                <div class="text-sm text-gray-700">Click a dip marker to inspect evidence</div>
              </div>
              <div class="text-xs text-gray-500">
                dips: <span class="font-medium text-gray-700">{{ summary?.meta?.dip_count ?? 0 }}</span>
              </div>
            </div>

            <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
              <!-- Chart -->
              <div class="lg:col-span-2">
                <RecoveryChart
                  :days="(timeseries?.days ?? [])"
                  :selectedDate="selectedDate"
                  @select="onSelectDate"
                />
              </div>

              <!-- Drilldown -->
              <div class="rounded-xl border border-gray-200 p-4">
                <div class="flex flex-row space-x-2 items-center">
                  <div class="text-sm font-medium">Day details</div>
                  <div class="text-xs text-gray-500">
                    {{ selectedDay ? selectedDay.date : 'Select a dip point' }}
                  </div>
                </div>
                <div class="mt-3 flex items-center gap-2">
                  <button
                    class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs hover:bg-gray-50 disabled:opacity-50"
                    @click="goPrevDay"
                    :disabled="selectedIndex <= 0"
                  >
                    Prev
                  </button>
                  <button
                    class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs hover:bg-gray-50 disabled:opacity-50"
                    @click="goNextDay"
                    :disabled="selectedIndex === -1 || selectedIndex >= days.length - 1"
                  >
                    Next
                  </button>

                  <button
                    class="ml-auto rounded-lg bg-black px-3 py-1.5 text-xs text-white hover:bg-black/90"
                    @click="goToToday"
                  >
                    Today
                  </button>
                </div>

                <div v-if="!selectedDay" class="mt-3 text-sm text-gray-600">
                  Click a <span class="font-medium">dip marker</span> on the chart to see what was abnormal that day.
                </div>

                <div v-else class="mt-3 space-y-3">
                  <div class="flex items-center">
                    <div class="text-xs text-gray-500 mr-2">Dip Classification:</div>
                    <div class="text-xs">
                      <span v-if="selectedDay.is_dip" class="rounded-lg bg-gray-100 px-2 py-1">
                        {{ selectedDay.dip_kind }}
                      </span>
                      <span v-else class="text-gray-400">—</span>
                    </div>
                  </div>

                  <div class="grid grid-cols-2 gap-2 text-sm">
                    <Metric label="Recovery" :value="fmt(selectedDay.recovery_value)" />
                    <Metric label="Exercise" :value="fmt(selectedDay.excercise_data_point) + ' cal'" />
                    <Metric label="Sleep" :value="fmt(selectedDay.sleep_duration) + ' hrs'" />
                    <Metric label="Nutrition" :value="fmtInt(selectedDay.nutrition_data_point) + ' cal'" />
                  </div>

                  <div class="pt-2 border-t border-gray-200">
                    <div class="text-xs text-gray-500">Deviation vs baseline</div>
                    <div class="mt-2 space-y-2">
                      <FactorFlag
                        v-for="k in ['exercise','sleep','nutrition']"
                        :key="k"
                        :name="k"
                        :abnormal="!!selectedDay.factor_abnormal?.[k]"
                        :z="selectedDay.factor_abs_z?.[k] ?? 0"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { useHealthApi, type Summary, type Timeseries, type TimeseriesDay } from '~/composables/useHealth'

const { getSummary, getTimeseries } = useHealthApi()

const userId = ref('user1')
const windowDays = ref(30)

type Scenario = {
  key: 'stable' | 'exercise' | 'sleep'
  label: string
  userId: string
}

const scenarios: Scenario[] = [
  { key: 'stable', label: 'Stable', userId: 'stable1' },
  { key: 'exercise', label: 'Exercise', userId: 'exercise1' },
  { key: 'sleep', label: 'Sleep', userId: 'sleep1' },
]

const activeScenario = ref<Scenario>(scenarios[1]!) // default = exercise demo

const selectScenario = async (s: Scenario) => {
  activeScenario.value = s
  userId.value = s.userId
  selectedDate.value = null
  windowDays.value = 45
  await refreshAll()
}


const MIN_WINDOW = 7

const sanitizeWindow = (raw: number, maxDays: number | null) => {
  let w = Number.isFinite(raw) ? Math.floor(raw) : MIN_WINDOW
  if (w < MIN_WINDOW) w = MIN_WINDOW
  if (maxDays != null && maxDays > 0 && w > maxDays) w = maxDays
  return w
}

const summary = ref<Summary | null>(null)
const timeseries = ref<Timeseries | null>(null)

const pending = ref(false)
const error = ref<string | null>(null)

const selectedDate = ref<string | null>(null)

const signal_strengthPillClass = computed(() => {
  const c = summary.value?.insight.signal_strength
  if (c === 'high') return 'bg-green-500 text-white'
  if (c === 'medium') return 'bg-yellow-500 text-white'
  return 'border-gray-200 bg-gray-50 text-gray-800'
})

const fmt = (v: number | null) => {
  if (v === null || Number.isNaN(v)) return '—'
  return Number(v).toFixed(2)
}

const fmtInt = (v: number | null) => {
  if (v === null || Number.isNaN(v)) return '—'
  return Math.round(Number(v)).toString()
}
const selectedDay = computed<TimeseriesDay | null>(() => {
  if (!selectedDate.value) return null
  return (timeseries.value?.days ?? []).find(d => d.date === selectedDate.value) ?? null
})

const onSelectDate = (d: string) => {
  selectedDate.value = d
}

const days = computed(() => timeseries.value?.days ?? [])

const selectedIndex = computed(() => {
  if (!selectedDate.value) return -1
  return days.value.findIndex(d => d.date === selectedDate.value)
})

const selectByIndex = (i: number) => {
  const arr = days.value
  if (!arr.length) return
  const idx = Math.max(0, Math.min(arr.length - 1, i))
  const day = arr[idx]
  if (day) {
    selectedDate.value = day.date
  }
}

const goPrevDay = () => selectByIndex(selectedIndex.value - 1)
const goNextDay = () => selectByIndex(selectedIndex.value + 1)

const isoToday = () => new Date().toISOString().slice(0, 10)

const goToToday = () => {
  const arr = days.value
  if (!arr.length) return
  const t = isoToday()
  const exact = arr.findIndex(d => d.date === t)
  if (exact !== -1) return selectByIndex(exact)

  // nearest past day
  let best = -1
  for (let i = 0; i < arr.length; i++) {
    const day = arr[i]
    if (day && day.date <= t) best = i
  }
  if (best !== -1) return selectByIndex(best)

  // else fall back to last
  selectByIndex(arr.length - 1)
}

const kpi = computed(() => {
  const mean = summary.value?.meta?.stability?.recovery_mean
  const std = summary.value?.meta?.stability?.recovery_std
  return {
    recoveryAvg: mean == null ? '—' : Number(mean).toFixed(1),
    recoveryStd: std == null ? '—' : Number(std).toFixed(1)
  }
})

const hasLoadedData = ref(false)
const lastLoadedWindow = ref<number | null>(null) // Track what window was actually loaded

const refreshAll = async () => {
  pending.value = true
  error.value = null

  try {
    const safeMin = Math.max(MIN_WINDOW, Number(windowDays.value) || MIN_WINDOW)

    const t = await getTimeseries(userId.value, safeMin)
    timeseries.value = t

    const maxDays = t.days?.length ?? 0

    const clamped = sanitizeWindow(windowDays.value, maxDays)
    if (clamped !== windowDays.value) windowDays.value = clamped

    const s = await getSummary(userId.value, clamped)
    summary.value = s
    
    hasLoadedData.value = true
    lastLoadedWindow.value = clamped  // Store the actual loaded window

    if (!selectedDate.value) {
      const firstDip = (t.days ?? []).find(d => d.is_dip)
      selectedDate.value = firstDip?.date ?? (t.days?.[0]?.date ?? null)
    }
  } catch (e: any) {
    error.value = e?.data?.detail || e?.message || 'Failed to fetch data.'
  } finally {
    pending.value = false
  }
}

onMounted(refreshAll)
</script>