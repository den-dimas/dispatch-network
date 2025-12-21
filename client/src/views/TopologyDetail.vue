<template>
  <div class="h-full flex flex-col" v-if="topology">
    <Teleport to="#sidebar-target">
      <div class="flex flex-col h-full">
        <div class="p-4 border-b space-y-4">
          <div class="flex items-center gap-2">
            <Button variant="ghost" size="icon" @click="$router.push('/')">
              <ArrowLeft class="h-5 w-5" />
            </Button>
            <h2 class="font-semibold truncate">{{ topology.name }}</h2>
          </div>

          <!-- Warnings Section -->
          <div v-if="warnings.length > 0" class="space-y-2">
            <div v-for="warning in warnings" :key="warning"
              class="flex items-center gap-2 p-2 rounded-md bg-amber-50 text-amber-700 text-xs border border-amber-200">
              <AlertCircle class="h-3 w-3 shrink-0" />
              <span>{{ warning }}</span>
            </div>
          </div>

          <!-- Error Section -->
          <div v-if="error" class="p-2 rounded-md bg-red-50 text-red-700 text-xs border border-red-200">
            <div class="flex items-center gap-2">
              <AlertCircle class="h-3 w-3 shrink-0" />
              <span>{{ error }}</span>
            </div>
          </div>

          <!-- Credentials Section -->
          <div class="p-3 rounded-md bg-muted/50 border space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-muted-foreground">Credentials</span>
              <Button variant="ghost" size="icon" class="h-6 w-6" @click="showUserModal = true">
                <Pencil class="h-3 w-3" />
              </Button>
            </div>
            <div class="space-y-1 text-xs">
              <div class="flex items-center gap-2">
                <span class="text-muted-foreground">User:</span>
                <span class="font-mono">{{ topology.username || 'Not set' }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-muted-foreground">Pass:</span>
                <span class="font-mono">{{ topology.password || 'Not set' }}</span>
              </div>
            </div>
          </div>

          <Button variant="outline" class="w-full justify-start" @click="showDevicesModal = true">
            <Server class="mr-2 h-4 w-4" />
            Devices
          </Button>

          <Button variant="default" class="w-full justify-start" @click="handleRefreshConfigs"
            :disabled="!canRefreshConfigs || hasActiveTask">
            <Loader2 v-if="hasActiveTask" class="mr-2 h-4 w-4 animate-spin" />
            <RefreshCw v-else class="mr-2 h-4 w-4" />
            Refresh Configs
          </Button>

          <!-- Task Progress -->
          <div v-if="currentTask"
            class="p-3 rounded-md bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-blue-700 dark:text-blue-300">Background Task</span>
              <span class="text-xs text-blue-600 dark:text-blue-400">{{ currentTask.progress }}%</span>
            </div>
            <div class="w-full bg-blue-200 dark:bg-blue-900 rounded-full h-1.5">
              <div class="bg-blue-600 dark:bg-blue-400 h-1.5 rounded-full transition-all duration-300"
                :style="{ width: currentTask.progress + '%' }"></div>
            </div>
            <p class="text-xs text-blue-700 dark:text-blue-300">{{ currentTask.message }}</p>
            <p v-if="currentTask.total_devices" class="text-xs text-blue-600 dark:text-blue-400">
              {{ currentTask.completed_devices }} / {{ currentTask.total_devices }} devices
            </p>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-4">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-medium text-muted-foreground">Chat Sessions</h3>
          </div>

          <div v-if="sessions.length === 0" class="text-center py-8 text-muted-foreground text-sm">
            <p>No chat sessions yet</p>
          </div>

          <div v-else class="space-y-2">
            <div v-for="session in sessions" :key="session.id"
              class="group flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground cursor-pointer"
              :class="{ 'bg-accent text-accent-foreground': chatStore.currentSession === session.id }"
              @click="selectSession(session)">
              <div class="flex items-center gap-2 truncate">
                <MessageSquare class="h-4 w-4" />
                <span class="truncate">{{ session.title }}</span>
              </div>
              <div class="flex gap-1 opacity-0 group-hover:opacity-100">
                <Button variant="ghost" size="icon" class="h-6 w-6" @click.stop="showRenameModal(session)">
                  <Pencil class="h-3 w-3 text-muted-foreground" />
                </Button>
                <Button variant="ghost" size="icon" class="h-6 w-6" @click.stop="showDeleteModal(session)">
                  <Trash2 class="h-3 w-3 text-muted-foreground hover:text-destructive" />
                </Button>
              </div>
            </div>
          </div>
        </div>

        <div class="p-4 border-t">
          <Button class="w-full" @click="startNewChat">
            <Plus class="mr-2 h-4 w-4" />
            New Chat
          </Button>
        </div>
      </div>
    </Teleport>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col bg-background h-full">
      <ChatPanel :topology-id="topologyId" class="h-full border-0 rounded-none" />
    </div>

    <DevicesListModal v-if="showDevicesModal" :topology-id="topologyId" :devices="devices" :loading="loading"
      @close="showDevicesModal = false" @refresh="loadData" />

    <SetUserModal v-if="showUserModal" :topology-id="topologyId" @close="showUserModal = false"
      @saved="handleUserCredentialsSaved" />

    <DeleteChatModal v-if="sessionToDelete" :session="sessionToDelete" @close="sessionToDelete = null"
      @delete="confirmDeleteSession" />

    <RenameChatModal v-if="sessionToRename" :session="sessionToRename" @close="sessionToRename = null"
      @rename="confirmRenameSession" />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useTopologyStore } from '../stores/topology';
import { useChatStore } from '../stores/chat';
import ChatPanel from '../components/ChatPanel.vue';
import DevicesListModal from '../components/DevicesListModal.vue';
import SetUserModal from '../components/SetUserModal.vue';
import DeleteChatModal from '../components/DeleteChatModal.vue';
import RenameChatModal from '../components/RenameChatModal.vue';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Plus, Trash2, Server, MessageSquare, AlertCircle, RefreshCw, Loader2, Pencil } from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();
const store = useTopologyStore();
const chatStore = useChatStore();

const topologyId = computed(() => route.params.id);
const topology = computed(() => store.currentTopology);
const devices = computed(() => store.devices);
const sessions = computed(() => chatStore.sessions);
const loading = ref(false);
const showDevicesModal = ref(false);
const showUserModal = ref(false);
const sessionToDelete = ref(null);
const sessionToRename = ref(null);
const error = ref(null);

const currentTask = computed(() => store.currentTask);
const hasActiveTask = computed(() => currentTask.value && currentTask.value.status === 'running');

// Check if user credentials are set
const hasUserCredentials = computed(() => {
  if (!topology.value) return false;
  return topology.value.username && topology.value.password;
});

// Can refresh configs only if credentials are set and devices exist
const canRefreshConfigs = computed(() => {
  return hasUserCredentials.value && devices.value.length > 0;
});

// Generate warnings
const warnings = computed(() => {
  const warns = [];
  if (!hasUserCredentials.value) {
    warns.push('Set username and password to access devices');
  }
  return warns;
});

const loadData = async () => {
  // loading.value = true;
  try {
    await store.fetchTopologyDetail(topologyId.value);
    await chatStore.fetchSessions(topologyId.value);

    // Show user modal if credentials not set
    if (!hasUserCredentials.value) {
      showUserModal.value = true;
    }
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
};

const showDeleteModal = (session) => {
  sessionToDelete.value = session;
};

const confirmDeleteSession = async () => {
  if (!sessionToDelete.value) return;

  const sessionId = sessionToDelete.value.id;
  await chatStore.deleteSession(topologyId.value, sessionId);

  if (chatStore.currentSession === sessionId) {
    chatStore.resetSession();
  }

  sessionToDelete.value = null;
};

const showRenameModal = (session) => {
  sessionToRename.value = session;
};

const confirmRenameSession = async (newTitle) => {
  if (!sessionToRename.value) return;

  await chatStore.renameSession(topologyId.value, sessionToRename.value.id, newTitle);
  sessionToRename.value = null;
};

const startNewChat = () => {
  chatStore.resetSession();
  chatStore.setCurrentSession('new');
};

const selectSession = async (session) => {
  chatStore.setCurrentSession(session.id);
  await chatStore.fetchHistory(topologyId.value, session.id);
};

const handleUserCredentialsSaved = async (credentials) => {
  error.value = null;
  try {
    await store.updateUserCredentials(topologyId.value, credentials);
    showUserModal.value = false;
  } catch (err) {
    console.error('Failed to save credentials:', err);
    error.value = err.response?.data?.detail || 'Failed to save credentials';
  }
};

const handleRefreshConfigs = async () => {
  if (!canRefreshConfigs.value || hasActiveTask.value) return;

  error.value = null;
  try {
    await store.refreshConfigs(topologyId.value);
  } catch (err) {
    console.error('Failed to refresh configs:', err);
    error.value = err.response?.data?.detail || 'Failed to refresh configs';
  }
};

onMounted(async () => {
  await loadData();
});
</script>
