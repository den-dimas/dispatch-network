<template>
  <Dialog :open="true" @update:open="$emit('close')">
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Add Device</DialogTitle>
        <DialogDescription>
          Add a new device to the topology.
        </DialogDescription>
      </DialogHeader>
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div class="space-y-2">
          <Label for="hostname">Hostname</Label>
          <Input id="hostname" v-model="form.hostname" required placeholder="router-01" />
        </div>
        <div class="space-y-2">
          <Label for="ip_address">IP Address</Label>
          <Input id="ip_address" v-model="form.ip_address" required placeholder="192.168.1.1" />
        </div>

        <div v-if="error" class="text-sm text-destructive">
          {{ error }}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" @click="$emit('close')">Cancel</Button>
          <Button type="submit" :disabled="loading">
            <Loader2 v-if="loading" class="mr-2 h-4 w-4 animate-spin" />
            Add Device
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>

<script setup>
import { ref } from 'vue';
import { useTopologyStore } from '../stores/topology';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2 } from 'lucide-vue-next';

const props = defineProps({
  topologyId: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['close', 'added']);
const store = useTopologyStore();

const form = ref({
  hostname: '',
  ip_address: ''
});

const loading = ref(false);
const error = ref(null);

const handleSubmit = async () => {
  loading.value = true;
  error.value = null;

  try {
    await store.addDevice(props.topologyId, form.value);
    emit('added');
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
};
</script>
