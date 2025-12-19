<template>
  <Dialog :open="true" @update:open="handleClose">
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Set Credentials</DialogTitle>
        <DialogDescription>
          Set the username and password for accessing devices in this topology.
        </DialogDescription>
      </DialogHeader>
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div class="space-y-2">
          <Label for="username">Username</Label>
          <Input id="username" v-model="form.username" required placeholder="admin" />
        </div>
        <div class="space-y-2">
          <Label for="password">Password</Label>
          <Input id="password" v-model="form.password" type="password" required placeholder="••••••••" />
        </div>

        <div v-if="error" class="text-sm text-destructive">
          {{ error }}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" @click="handleClose" :disabled="loading">Cancel</Button>
          <Button type="submit" :disabled="loading">
            <Loader2 v-if="loading" class="mr-2 h-4 w-4 animate-spin" />
            Save Credentials
          </Button>
        </DialogFooter>
      </form>
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2 } from 'lucide-vue-next';

const props = defineProps({
  topologyId: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['close', 'saved']);

const form = ref({
  username: '',
  password: ''
});

const loading = ref(false);
const error = ref(null);

const handleSubmit = async () => {
  loading.value = true;
  error.value = null;

  try {
    emit('saved', form.value);
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
};

const handleClose = () => {
  if (!loading.value) {
    emit('close');
  }
};
</script>
