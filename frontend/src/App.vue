<script setup>
import AIAssistantWidget from './components/AIAssistantWidget.vue'
import GlobalFeedback from './components/GlobalFeedback.vue'
</script>

<template>
  <GlobalFeedback />
  <router-view />
  <AIAssistantWidget />
</template>
