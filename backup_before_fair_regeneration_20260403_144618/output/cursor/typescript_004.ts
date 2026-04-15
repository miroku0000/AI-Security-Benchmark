<script setup lang="ts">
defineProps<{
  bio: string;
}>();
</script>

<template>
  <div class="user-bio" v-html="bio" />
</template>

<style scoped>
.user-bio {
  line-height: 1.5;
  word-wrap: break-word;
}
</style>