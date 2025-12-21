<template>
  <div class="space-y-6 p-6">
    <div class="flex justify-between items-center">
      <h2 class="text-3xl font-bold tracking-tight text-foreground">Network Topologies</h2>
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <Loader2 class="h-8 w-8 animate-spin text-primary" />
    </div>

    <div v-else-if="error" class="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
      {{ error }}
    </div>

    <div v-else-if="topologies.length === 0" class="text-center py-12 text-muted-foreground">
      <FolderPlus class="mx-auto h-12 w-12 opacity-50" />
      <h3 class="mt-4 text-lg font-semibold">No topologies yet</h3>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <Card v-for="topology in topologies" :key="topology.project_id" @click="selectTopology(topology)"
        class="cursor-pointer hover:bg-accent/50 transition-colors border-border bg-card">
        <CardHeader class="flex flex-row items-center justify-between space-y-0 p-6">
          <CardTitle class="text-xl font-semibold text-card-foreground">
            {{ topology.name }}
          </CardTitle>
          <ChevronRight class="h-5 w-5 text-muted-foreground" />
        </CardHeader>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useTopologyStore } from '../stores/topology';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, FolderPlus, ChevronRight } from 'lucide-vue-next';

const router = useRouter();
const store = useTopologyStore();

const topologies = ref([]);
const loading = ref(false);
const error = ref(null);

const loadTopologies = async () => {
  loading.value = true;
  error.value = null;
  try {
    await store.fetchTopologies();
    topologies.value = store.topologies;
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
};

const selectTopology = (topology) => {
  store.setCurrentTopology(topology);
  router.push(`/topology/${topology.project_id}`);
};

onMounted(() => {
  loadTopologies();
});
</script>
