<script setup lang="ts">
withDefaults(defineProps<{
  label: string
  value: string | number
  unit?: string
  sub?: string
  trend?: { delta: string | number; direction: 'up' | 'down' | 'flat' }
  tone?: 'default' | 'brand' | 'success' | 'warn' | 'danger'
}>(), { unit: '', sub: '', tone: 'default' })
</script>

<template>
  <article class="stat-card data-card" :class="`tone-${tone}`">
    <div class="stat-card-head"><span>{{ label }}</span><slot name="visual" /></div>
    <div class="stat-card-value"><strong>{{ value }}</strong><small v-if="unit">{{ unit }}</small></div>
    <div class="stat-card-context">
      <span v-if="trend" class="stat-trend" :class="`is-${trend.direction}`">
        <b aria-hidden="true">{{ trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→' }}</b>{{ trend.delta }}
      </span>
      <span>{{ sub || '未记录对比数据' }}</span>
    </div>
    <slot />
  </article>
</template>
