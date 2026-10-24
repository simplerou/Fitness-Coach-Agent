<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { activeModuleKey, adminGroup, moduleGroups } from '@/utils/moduleNavigation'
import NavIcon from './NavIcon.vue'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const groups = computed(() => auth.isAdmin ? [...moduleGroups, adminGroup] : moduleGroups)
const active = computed(() => activeModuleKey(route))
const expanded = ref<Record<string, boolean>>({})
watch([active, () => auth.isAdmin], () => {
  if (!auth.isAdmin) delete expanded.value.admin
  const group = groups.value.find(item => item.children.some(child => child.key === active.value))
  if (group) expanded.value[group.key] = true
}, { immediate: true })
function go(to: RouteLocationRaw) { void router.push(to); emit('close') }
</script>

<template>
  <aside class="app-sidebar" :class="{ open }" aria-label="主导航">
    <div class="sidebar-brand">
      <span class="brand-mark">禾</span><span><strong>青禾</strong><small>训练助理</small></span>
      <button class="sidebar-close" aria-label="关闭导航" @click="emit('close')"><NavIcon name="close" /></button>
    </div>
    <nav class="sidebar-nav">
      <button type="button" :class="{ active: active === 'today' }" :aria-current="active === 'today' ? 'page' : undefined" title="概览" @click="go({ name: 'today' })"><NavIcon name="overview" /><span>概览</span></button>
      <div v-for="group in groups.filter(item => item.key !== 'admin')" :key="group.key" class="sidebar-module-group">
        <button type="button" class="sidebar-module-toggle" :class="{ active: group.children.some(item => item.key === active) }" :aria-expanded="!!expanded[group.key]" :aria-controls="'sidebar-modules-' + group.key" @click="expanded[group.key] = !expanded[group.key]">
          <NavIcon :name="group.icon" /><span>{{ group.label }}</span>
          <svg class="sidebar-module-chevron" :class="{ expanded: expanded[group.key] }" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m6 8 4 4 4-4" /></svg>
        </button>
        <div v-show="expanded[group.key]" :id="'sidebar-modules-' + group.key" class="sidebar-submodules" role="group" :aria-label="group.label + '子模块'">
          <button v-for="item in group.children" :key="item.key" type="button" :class="{ active: active === item.key }" :aria-current="active === item.key ? 'page' : undefined" @click="go(item.to)"><NavIcon :name="group.icon" /><span>{{ item.label }}</span></button>
        </div>
      </div>
      <button type="button" :class="{ active: active === 'library' }" :aria-current="active === 'library' ? 'page' : undefined" title="动作库" @click="go({ name: 'library' })"><NavIcon name="library" /><span>动作库</span></button>
      <div v-if="auth.isAdmin" class="sidebar-module-group">
        <button type="button" class="sidebar-module-toggle" :class="{ active: route.meta.requiresAdmin }" :aria-expanded="!!expanded.admin" aria-controls="sidebar-modules-admin" @click="expanded.admin = !expanded.admin">
          <NavIcon name="settings" /><span>管理中心</span>
          <svg class="sidebar-module-chevron" :class="{ expanded: expanded.admin }" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m6 8 4 4 4-4" /></svg>
        </button>
        <div v-show="expanded.admin" id="sidebar-modules-admin" class="sidebar-submodules" role="group" aria-label="管理中心子模块">
          <button v-for="item in adminGroup.children" :key="item.key" type="button" :class="{ active: active === item.key }" :aria-current="active === item.key ? 'page' : undefined" @click="go(item.to)"><NavIcon :name="item.key === 'admin' ? 'overview' : 'library'" /><span>{{ item.label }}</span></button>
        </div>
      </div>
    </nav>
    <div class="sidebar-bottom"><p>本机演示 · 不构成医疗建议</p></div>
  </aside>
  <button v-if="open" class="sidebar-backdrop" aria-label="关闭导航" @click="emit('close')"></button>
</template>
