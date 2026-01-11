<template>
  <div class="flex items-center justify-between rounded-lg border border-gray-200 px-3 py-2">
    <div class="flex items-center gap-2">
      <div class="text-sm font-medium capitalize">{{ name }}</div>

      <span
        class="inline-flex items-center gap-1 rounded-lg px-2 py-0.5 text-xs"
        :class="abnormal ? 'bg-orange-500 text-white' : 'bg-green-500 text-white'"
      >
        {{ abnormal ? 'abnormal' : 'normal' }}
      </span>
    </div>

    <div class="flex items-center gap-1 text-xs text-gray-500 tabular-nums">
      <span>|z| {{ z.toFixed(2) }}</span>
      <TooltipIcon :text="zTooltip" />
    </div>
  </div>
</template>

<script setup lang="ts">
import TooltipIcon from '~/components/TooltipIcon.vue'

const props = defineProps<{ name: string; abnormal: boolean; z: number }>()

const normalityTooltip = computed(() => {
  return props.abnormal
    ? 'Abnormal means this metric deviated meaningfully from your personal baseline on this day.'
    : 'Normal means this metric was close to your personal baseline on this day.'
})

const zTooltip = computed(() => {
  return '|z| is the number of standard deviations this value is from your baseline. Larger values indicate stronger deviation.'
})
</script>

