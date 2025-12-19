<template>
  <div class="flex flex-col h-full">
    <div class="p-4 border-b bg-muted/30 space-y-3">
      <div v-if="!chatStore.sessionStarted" class="flex gap-4 items-center">
        <div class="flex-1">
          <label class="text-xs font-medium mb-1.5 block">Model</label>
          <select v-model="chatStore.selectedModel" @change="handleModelChange"
            class="w-full px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary">
            <option value="qwen">Qwen</option>
            <option value="deepseek">DeepSeek</option>
            <option value="gemma">Gemma</option>
          </select>
        </div>
        <div class="flex-1">
          <label class="text-xs font-medium mb-1.5 block">Mode</label>
          <select v-model="chatStore.selectedMode" @change="handleModeChange"
            class="w-full px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary">
            <option value="ask">Ask (Fast)</option>
            <option value="agent">Agent (With Tools)</option>
          </select>
        </div>
      </div>
      <div v-else class="flex gap-2 items-center justify-center py-1">
        <span class="text-xs font-medium px-2 py-1 rounded-md bg-primary/10 text-primary">{{
          getModelLabel(chatStore.selectedModel) }}</span>
        <span class="text-xs text-muted-foreground">•</span>
        <span class="text-xs font-medium px-2 py-1 rounded-md bg-primary/10 text-primary">{{
          getModeLabel(chatStore.selectedMode) }}</span>
      </div>
      <p v-if="!chatStore.sessionStarted" class="text-xs text-muted-foreground">
        Settings are locked once the chat session starts
      </p>
    </div>
    <div class="flex-1 overflow-y-auto p-4 space-y-6" ref="messageContainer">
      <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full text-muted-foreground">
        <div class="bg-muted/50 p-4 rounded-full mb-4">
          <MessageSquare class="h-8 w-8 opacity-50" />
        </div>
        <h3 class="text-lg font-semibold">Welcome to Dispatch AI</h3>
        <p class="text-sm mt-1">Ask questions about your network topology</p>
      </div>

      <div v-for="(message, index) in messages" :key="index" class="max-w-3xl mx-auto w-full">
        <!-- User Message -->
        <div v-if="message.role === 'user'" class="flex justify-end mb-6">
          <div class="rounded-2xl px-4 py-3 bg-primary text-primary-foreground shadow-sm max-w-[80%]">
            <div class="text-sm whitespace-pre-wrap break-words leading-relaxed">{{ message.content }}</div>
          </div>
        </div>

        <!-- AI Message -->
        <div v-else class="mb-6">
          <MessageContent :content="message.content" :mode="chatStore.selectedMode" />
        </div>
      </div>

      <div v-if="streaming" class="max-w-3xl mx-auto w-full mb-6">
        <div class="flex gap-1">
          <div class="w-2 h-2 bg-foreground/50 rounded-full animate-bounce"></div>
          <div class="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
          <div class="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
        </div>
      </div>
    </div>

    <div class="p-4 border-t bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/60">
      <div class="max-w-3xl mx-auto w-full">
        <div v-if="streaming && chatStore.selectedMode === 'agent'" class="mb-3 flex justify-center">
          <Button variant="destructive" size="sm" @click="handleStopAgent">
            <XCircle class="mr-2 h-4 w-4" />
            Stop Agent
          </Button>
        </div>
        <form @submit.prevent="handleSend" class="relative">
          <textarea v-model="inputMessage" :disabled="streaming" placeholder="Message Dispatch AI..."
            @keydown="handleKeyDown"
            class="w-full pr-12 px-4 py-3 rounded-xl bg-muted/50 border-0 focus-visible:ring-1 focus-visible:ring-primary shadow-inner resize-none min-h-[56px] max-h-[200px] leading-relaxed"
            rows="1"></textarea>
          <Button type="submit" :disabled="!inputMessage.trim() || streaming" size="icon"
            class="absolute right-2 bottom-2 h-8 w-8 rounded-lg transition-all"
            :class="inputMessage.trim() ? 'opacity-100' : 'opacity-50'">
            <Send class="h-4 w-4" />
          </Button>
        </form>
        <p class="text-xs text-center text-muted-foreground mt-2">
          AI can make mistakes. Please review generated responses.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { useChatStore } from '../stores/chat';
import MessageContent from './MessageContent.vue';
import { Button } from '@/components/ui/button';
import { MessageSquare, Send, XCircle } from 'lucide-vue-next';

const props = defineProps({
  topologyId: {
    type: String,
    required: true
  }
});

const chatStore = useChatStore();
const inputMessage = ref('');
const messageContainer = ref(null);

const messages = computed(() => chatStore.messages);
const streaming = computed(() => chatStore.streaming);

const handleModelChange = () => {
  chatStore.setModel(chatStore.selectedModel);
};

const handleModeChange = () => {
  chatStore.setMode(chatStore.selectedMode);
};

const getModelLabel = (model) => {
  const labels = {
    qwen: 'Qwen',
    deepseek: 'DeepSeek',
    gemma: 'Gemma'
  };
  return labels[model] || model;
};

const getModeLabel = (mode) => {
  const labels = {
    ask: 'Ask Mode',
    agent: 'Agent Mode'
  };
  return labels[mode] || mode;
};

const handleKeyDown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
};

const handleSend = async () => {
  if (!inputMessage.value.trim() || streaming.value) return;

  const message = inputMessage.value;
  inputMessage.value = '';

  try {
    const sessionId = chatStore.currentSession || 'new';
    const newSessionId = await chatStore.sendMessage(props.topologyId, sessionId, message);

    if (sessionId === 'new') {
      await chatStore.fetchSessions(props.topologyId);
    }
  } catch (error) {
    console.error('Failed to send message:', error);
  }
};

const handleStopAgent = async () => {
  try {
    await chatStore.stopAgent(props.topologyId);
  } catch (error) {
    console.error('Failed to stop agent:', error);
  }
};

const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTop = messageContainer.value.scrollHeight;
    }
  });
};

watch(messages, () => {
  scrollToBottom();
}, { deep: true });
</script>
