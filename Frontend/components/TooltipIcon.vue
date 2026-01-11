<template>
  <div class="relative inline-flex items-center">
    <button
      type="button"
      @click="open = !open"
      class="flex items-center justify-center text-current hover:opacity-100"
      aria-label="Explain metric"
    >
      <Info class="h-3.5 w-3.5 opacity-80" aria-hidden="true" />
    </button>

    <div
      v-if="open"
      class="absolute z-20 bottom-full right-0 mb-6 w-60
             rounded-lg border border-gray-200 bg-white
             px-3 py-2 text-xs text-gray-700 shadow-sm"
    >
      {{ text }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Info } from 'lucide-vue-next'

defineProps<{ text: string }>()

const open = ref(false)
</script>