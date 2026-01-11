<template>
  <div class="rounded-xl border-2 border-gray-200 p-4">
    <div class="flex items-center gap-2 text-sm font-semibold text-gray-500 justify-between">
      <span>{{ label }}</span>
      <TooltipIcon v-if="tooltip" :text="tooltip" />
    </div>

    <div class="mt-1 flex items-center gap-2">
      <div class="text-lg font-medium tracking-tight" :class="{ capitalize }">
        {{ value }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">

defineProps<{
  label: string
  value: string
  sub?: string              
  tooltip?: string          
  capitalize?: boolean
}>()
</script>
