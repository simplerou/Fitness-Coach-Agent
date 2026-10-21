<script setup lang="ts">
defineProps<{ title: string; breadcrumbs?: string[]; description?: string }>()
</script>

<template>
  <header class="page-header">
    <div>
      <nav v-if="breadcrumbs?.length" aria-label="面包屑">
        <span v-for="item in breadcrumbs" :key="item">{{ item }}</span>
      </nav>
      <h2>{{ title }}</h2>
      <p v-if="description">{{ description }}</p>
    </div>
    <div class="page-header-actions"><slot name="actions" /></div>
  </header>
</template>
