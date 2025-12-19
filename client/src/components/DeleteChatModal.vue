<template>
  <Dialog :open="true" @update:open="handleClose">
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Delete Chat Session</DialogTitle>
        <DialogDescription>
          Are you sure you want to delete this chat session? This action cannot be undone.
        </DialogDescription>
      </DialogHeader>
      
      <div class="py-4">
        <p class="text-sm font-medium">{{ session.title }}</p>
        <p class="text-xs text-muted-foreground mt-1">
          Created {{ formatDate(session.created_at) }}
        </p>
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" @click="handleClose" :disabled="loading">Cancel</Button>
        <Button type="button" variant="destructive" @click="handleDelete" :disabled="loading">
          <Loader2 v-if="loading" class="mr-2 h-4 w-4 animate-spin" />
          Delete
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref } from 'vue';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-vue-next';

const props = defineProps({
  session: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['close', 'delete']);

const loading = ref(false);

const handleDelete = async () => {
  loading.value = true;
  try {
    emit('delete');
  } finally {
    loading.value = false;
  }
};

const handleClose = () => {
  if (!loading.value) {
    emit('close');
  }
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  
  return date.toLocaleDateString();
};
</script>
