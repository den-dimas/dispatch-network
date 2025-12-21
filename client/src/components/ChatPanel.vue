<template>
  <div class="flex flex-col h-full relative">
    <!-- Header with Settings -->
    <div class="absolute top-4 right-4 z-10">
      <Dialog>
        <DialogTrigger as-child>
          <Button variant="outline" size="icon" class="rounded-full bg-background/50 backdrop-blur hover:bg-background">
            <Settings class="h-4 w-4" />
          </Button>
        </DialogTrigger>
        <DialogContent class="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Chat Configuration</DialogTitle>
          </DialogHeader>
          <div class="grid gap-4 py-4">
            <div class="space-y-2">
              <label
                class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">Model</label>
              <select v-model="chatStore.selectedModel" @change="handleModelChange" :disabled="chatStore.sessionStarted"
                class="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                <option value="qwen">Qwen</option>
                <option value="deepseek">DeepSeek</option>
                <option value="gemma">Gemma</option>
              </select>
            </div>
            <div class="space-y-2">
              <label
                class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">Mode</label>
              <select v-model="chatStore.selectedMode" @change="handleModeChange" :disabled="chatStore.sessionStarted"
                class="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                <option value="ask">Ask (Fast)</option>
                <option value="agent">Agent (With Tools)</option>
              </select>
            </div>
            <p v-if="chatStore.sessionStarted" class="text-xs text-muted-foreground">
              Settings are locked once the chat session starts
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>

    <!-- Messages Area -->
    <div class="flex-1 overflow-y-auto p-4 pb-32 space-y-6" ref="messageContainer">
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
          <div class="rounded-2xl px-5 py-3 bg-muted text-foreground max-w-[80%]">
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

    <!-- Floating Input Area -->
    <div
      class="absolute bottom-0 left-0 w-full p-4 bg-gradient-to-t from-background via-background/90 to-transparent z-20">
      <div class="max-w-3xl mx-auto w-full">
        <div v-if="streaming && chatStore.selectedMode === 'agent'" class="mb-3 flex justify-center">
          <Button variant="destructive" size="sm" @click="handleStopAgent" class="rounded-full shadow-md">
            <XCircle class="mr-2 h-4 w-4" />
            Stop Agent
          </Button>
        </div>

        <div
          class="bg-card rounded-3xl shadow-lg border border-border p-2 flex items-end gap-2 transition-all focus-within:shadow-xl focus-within:border-primary/50">
          <textarea v-model="inputMessage" :disabled="streaming" placeholder="Message Dispatch AI..."
            @keydown="handleKeyDown" @input="adjustHeight"
            class="flex-1 bg-transparent border-none focus:ring-0 resize-none py-3 px-4 max-h-[200px] min-h-[24px] text-foreground placeholder:text-muted-foreground focus:outline-none"
            rows="1" style="height: auto;"></textarea>
          <Button @click="handleSend" :disabled="!inputMessage.trim() || streaming" size="icon"
            class="rounded-full h-10 w-10 shrink-0 mb-1 mr-1 transition-all"
            :class="inputMessage.trim() ? 'opacity-100' : 'opacity-50'">
            <Send class="h-4 w-4" />
          </Button>
        </div>
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { MessageSquare, Send, XCircle, Settings } from 'lucide-vue-next';

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

const adjustHeight = (e) => {
  const textarea = e.target;
  textarea.style.height = 'auto';
  textarea.style.height = textarea.scrollHeight + 'px';
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

  // Reset height
  nextTick(() => {
    const textarea = document.querySelector('textarea');
    if (textarea) textarea.style.height = 'auto';
  });

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
