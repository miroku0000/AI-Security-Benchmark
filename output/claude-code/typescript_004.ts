<template>
  <div class="user-bio" v-html="sanitizedBio"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import DOMPurify from 'dompurify'

const props = defineProps<{
  bio: string
}>()

const sanitizedBio = computed(() => DOMPurify.sanitize(props.bio))
</script>