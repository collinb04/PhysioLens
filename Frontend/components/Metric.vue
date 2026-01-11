<template>
  <div class="rounded-lg border border-gray-200 px-3 py-2">
    <div class="text-[11px] text-gray-500">{{ label }}</div>
    <div class="mt-0.5 text-sm font-medium tabular-nums">{{ value }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; value: string }>()
</script>
