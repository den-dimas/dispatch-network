<template>
  <div class="flex h-screen bg-background font-sans antialiased overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-80 bg-card border-r border-border flex flex-col hidden md:flex z-20">
      <div class="p-4 border-b border-border flex items-center gap-3">
        <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shadow-sm">
          <span class="text-primary-foreground font-bold">D</span>
        </div>
        <h1 class="text-xl font-bold text-foreground tracking-tight">
          Dispatch
        </h1>
      </div>

      <nav class="flex-1 overflow-y-auto p-4 space-y-2">
        <div v-if="$route.path === '/'">
          <router-link to="/" class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
            :class="$route.path === '/' ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'">
            <LayoutGrid class="h-4 w-4" />
            Topologies
          </router-link>
        </div>
        <div id="sidebar-target"></div>
      </nav>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col min-w-0 overflow-hidden relative">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { LayoutGrid } from 'lucide-vue-next';
</script>
