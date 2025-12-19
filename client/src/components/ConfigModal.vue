<template>
  <Dialog :open="true" @update:open="$emit('close')">
    <DialogContent class="sm:max-w-[800px] max-h-[80vh] flex flex-col">
      <DialogHeader>
        <DialogTitle>{{ device.hostname }}</DialogTitle>
        <DialogDescription>
          {{ device.type }} - Port: {{ device.port }}
        </DialogDescription>
      </DialogHeader>

      <div class="flex-1 overflow-y-auto p-1">
        <pre class="bg-muted border rounded-lg p-4 text-sm overflow-x-auto">{{ device.latest_config }}</pre>
      </div>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

defineProps({
  device: {
    type: Object,
    required: true
  }
});

defineEmits(['close']);
</script>
