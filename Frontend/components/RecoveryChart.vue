<template>
  <div class="rounded-xl border border-gray-200 p-4 h-full flex flex-col justify-between">
    <div class="flex items-center justify-between">
      <div class="text-sm font-medium">Recovery</div>
      <div class="text-xs text-gray-500">Recovery Scores: min {{ minY.toFixed(0) }} • max {{ maxY.toFixed(0) }}</div>
    </div>

    <svg
      class="mt-3 w-full"
      style="height: 180px;"
      viewBox="0 0 1000 260"
      preserveAspectRatio="none"
    >
      <defs>
        <!-- Gradient for area fill -->
        <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#000000" stop-opacity="0.08" />
          <stop offset="100%" stop-color="#000000" stop-opacity="0" />
        </linearGradient>
        
        <!-- Drop shadow for line -->
        <filter id="lineShadow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
          <feOffset dx="0" dy="1" result="offsetblur"/>
          <feComponentTransfer>
            <feFuncA type="linear" slope="0.2"/>
          </feComponentTransfer>
          <feMerge>
            <feMergeNode/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      <!-- Grid -->
      <g opacity="0.06" stroke="#94a3b8" stroke-width="1">
        <line v-for="x in 10" :key="'vx'+x" :x1="x*100" y1="0" :x2="x*100" y2="260" />
        <line v-for="y in 6" :key="'hy'+y" x1="0" :y1="y*43.33" x2="1000" :y2="y*43.33" />
      </g>

      <!-- Area fill under line -->
      <path 
        :d="areaD" 
        fill="url(#areaGradient)" 
      />

      <!-- Recovery line -->
      <path 
        :d="pathD" 
        fill="none" 
        stroke="#000000" 
        stroke-width="2.5" 
        stroke-linecap="round" 
        stroke-linejoin="round"
        filter="url(#lineShadow)"
      />

      <!-- Dip markers -->
      <g v-for="p in points" :key="p.date">
        <!-- Actual marker dot -->
        <circle
          v-if="p.isDip"
          :cx="p.x"
          :cy="p.y"
          r="6"
          class="cursor-pointer"
          :class="dipFillClass(p)"
          stroke="#ffffff"
          stroke-width="2"
          @click="$emit('select', p.date)"
        />
        
        <!-- Selection ring -->
        <circle
          v-if="selectedDate && p.date === selectedDate"
          :cx="p.x"
          :cy="p.y"
          r="11"
          fill="none"
          :stroke="dipStrokeColor(p)"
          stroke-width="2.5"
          opacity="0.8"
        />
      </g>
    </svg>

    <div class="mt-2 flex items-center text-xs space-x-4">
      <div class="text-gray-500">
        Largest abnormal score index:
      </div>
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-1.5">
          <div class="w-2 h-2 rounded-lg bg-blue-500"></div>
          <span class="text-gray-600">Exercise (Act. calories burned)</span>
        </div>
        <div class="flex items-center gap-1.5">
          <div class="w-2 h-2 rounded-lg bg-purple-500"></div>
          <span class="text-gray-600">Sleep (Hours)</span>
        </div>
        <div class="flex items-center gap-1.5">
          <div class="w-2 h-2 rounded-lg bg-yellow-500"></div>
          <span class="text-gray-600">Nutrition (Calories Consumed)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type Day = {
  date: string
  recovery_value: number | null
  is_dip: boolean
  factor_abs_z?: {
    exercise?: number
    sleep?: number
    nutrition?: number
  }
}

const props = defineProps<{
  days: Day[]
  selectedDate: string | null
}>()

defineEmits<{ (e: 'select', date: string): void }>()

const filtered = computed(() =>
  (props.days ?? []).filter(d => typeof d.recovery_value === 'number')
)

const minY = computed(() => {
  const ys = filtered.value.map(d => d.recovery_value as number)
  return ys.length ? Math.min(...ys) : 0
})

const maxY = computed(() => {
  const ys = filtered.value.map(d => d.recovery_value as number)
  return ys.length ? Math.max(...ys) : 100
})

const points = computed(() => {
  const f = filtered.value
  if (!f.length) return []
  
  const range = maxY.value - minY.value || 1
  const w = 1000
  const h = 260
  
  return f.map((d, i) => ({
    date: d.date,
    isDip: d.is_dip,
    factor_abs_z: d.factor_abs_z,
    x: (i / Math.max(f.length - 1, 1)) * w,
    y: h - ((d.recovery_value! - minY.value) / range) * h
  }))
})

const dipFillClass = (p: any) => {
  const z = p.factor_abs_z || {}
  const ez = Number(z.exercise ?? 0)
  const sz = Number(z.sleep ?? 0)
  const nz = Number(z.nutrition ?? 0)
  const max = Math.max(ez, sz, nz)
  
  if (max <= 0) return 'fill-gray-500'
  if (max === ez) return 'fill-blue-500'
  if (max === sz) return 'fill-purple-500'
  return 'fill-yellow-500'
}

const dipStrokeColor = (p: any) => {
  const z = p.factor_abs_z || {}
  const ez = Number(z.exercise ?? 0)
  const sz = Number(z.sleep ?? 0)
  const nz = Number(z.nutrition ?? 0)
  const max = Math.max(ez, sz, nz)
  
  if (max <= 0) return '#6b7280'
  if (max === ez) return '#3b82f6'
  if (max === sz) return '#a855f7'
  return '#F7B500'
}

const pathD = computed(() => {
  const ps = points.value
  if (!ps.length) return ''
  return ps
    .map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(' ')
})

const areaD = computed(() => {
  const ps = points.value
  if (!ps || ps.length === 0) return ''
  
  const linePath = ps
    .map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(' ')
  
  const lastPoint = ps[ps.length - 1]
  const firstPoint = ps[0]
  
  if (!lastPoint || !firstPoint) return ''
  
  return `${linePath} L ${lastPoint.x.toFixed(2)} 260 L ${firstPoint.x.toFixed(2)} 260 Z`
})
</script>

<style scoped>
/* No custom animations needed */
</style>