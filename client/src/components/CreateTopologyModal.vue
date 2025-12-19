<template>
  <Dialog :open="true" @update:open="$emit('close')">
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Create Topology</DialogTitle>
        <DialogDescription>
          Enter the details for the new network topology.
        </DialogDescription>
      </DialogHeader>
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div class="space-y-2">
          <Label for="title">Title</Label>
          <Input id="title" v-model="form.title" required placeholder="Production Network" />
        </div>
        <div class="space-y-2">
          <Label for="description">Description</Label>
          <Textarea id="description" v-model="form.description" placeholder="Main production topology" />
        </div>
        <div class="space-y-2">
          <Label for="username">Username</Label>
          <Input id="username" v-model="form.username" required placeholder="admin" />
        </div>
        <div class="space-y-2">
          <Label for="password">Password</Label>
          <Input id="password" type="password" v-model="form.password" required placeholder="••••••••" />
        </div>

        <div v-if="error" class="text-sm text-destructive">
          {{ error }}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" @click="$emit('close')">Cancel</Button>
          <Button type="submit" :disabled="loading">
            <Loader2 v-if="loading" class="mr-2 h-4 w-4 animate-spin" />
            Create
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
import { Textarea } from '@/components/ui/textarea';
import { Loader2 } from 'lucide-vue-next';

const emit = defineEmits(['close', 'created']);
const store = useTopologyStore();

const form = ref({
  title: '',
  description: '',
  username: '',
  password: ''
});

const loading = ref(false);
const error = ref(null);

const handleSubmit = async () => {
  loading.value = true;
  error.value = null;

  try {
    await store.createTopology(form.value);
    emit('created');
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
};
</script>
