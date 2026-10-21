<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Drawer from './Drawer.vue'

const open = ref(false)
const query = ref('')
const router = useRouter()
const items = [
  ['概览', 'today'], ['周计划', 'plan'], ['训练记录', 'log'], ['饮食', 'diet'],
  ['报告与体测', 'shaping'], ['周回顾', 'review'], ['动作库', 'library'], ['设置', 'profile'],
] as const
const filtered = computed(() => items.filter((row) => row[0].includes(query.value.trim())))
function key(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    open.value = !open.value
  }
}
function go(name: string) { open.value = false; void router.push({ name }) }
onMounted(() => document.addEventListener('keydown', key))
onBeforeUnmount(() => document.removeEventListener('keydown', key))
</script>

<template>
  <slot :open="() => open = true" />
  <Drawer :open="open" title="搜索与跳转" @close="open = false">
    <label class="command-search"><span class="sr-only">搜索页面</span><input v-model="query" type="search" placeholder="搜索页面或功能" autofocus /></label>
    <div class="command-results"><button v-for="item in filtered" :key="item[1]" @click="go(item[1])"><span>{{ item[0] }}</span><kbd>Enter</kbd></button></div>
  </Drawer>
</template>
