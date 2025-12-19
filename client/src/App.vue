<template>
  <div class="min-h-screen bg-background font-sans antialiased">
    <nav
      class="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16 items-center">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <span class="text-primary-foreground font-bold">D</span>
            </div>
            <h1 class="text-xl font-bold text-foreground">
              Dispatch
            </h1>
          </div>
          <div class="flex gap-2">
            <router-link to="/" class="px-4 py-2 rounded-md text-sm font-medium transition-colors"
              :class="$route.path === '/' ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'">
              Topologies
            </router-link>
          </div>
        </div>
      </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>
