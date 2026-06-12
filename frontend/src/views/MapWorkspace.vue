<script setup lang="ts">
import RailwayMap from '@/components/RailwayMap.vue'
import TrainSearchPanel from '@/components/TrainSearchPanel.vue'
</script>

<template>
  <main class="workspace">
    <TrainSearchPanel />
    <RailwayMap />
  </main>
</template>

<style scoped>
.workspace {
  display: flex;
  width: 100vw;
  min-height: 100vh;
  overflow: hidden;
}

@media (max-width: 860px) {
  .workspace {
    flex-direction: column;
  }
}
</style>
