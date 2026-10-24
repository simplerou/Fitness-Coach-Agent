<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>
<template>
  <nav class="admin-section-nav" aria-label="管理员功能">
    <RouterLink to="/admin" exact-active-class="is-active">用户管理</RouterLink>
    <RouterLink to="/admin/knowledge" exact-active-class="is-active">RAG 知识库</RouterLink>
  </nav>
</template>
