<script setup lang="ts">
const days = ['一', '二', '三', '四', '五', '六', '日']
</script>

<template>
  <figure class="lp-preview" aria-label="青禾工作台功能示意，所示数据仅用于介绍产品">
    <div class="lp-preview-bar"><span class="lp-window-dots" aria-hidden="true"><i/><i/><i/></span><span>青禾 · 我的工作台</span><span class="lp-demo-tag">界面示意</span></div>
    <div class="lp-preview-body">
      <div class="lp-preview-heading"><div><small>每一步，都算数</small><h2>今天，练得更有方向。</h2></div><span class="lp-preview-avatar" aria-hidden="true">禾</span></div>
      <div class="lp-preview-stats"><div><small>今日训练</small><strong>全身力量</strong><span>3 个动作 · 约 40 分钟</span></div><div><small>饮食目标</small><strong>1,800 <em>kcal</em></strong><span>训练与饮食，一起安排</span></div></div>
      <div class="lp-chart-heading"><b>把变化，放进时间里看</b><span>体重趋势 / 8 周</span></div>
      <svg class="lp-preview-chart" viewBox="0 0 480 150" role="img" aria-label="示意趋势线：体重在八周内波动下降，不代表实际效果承诺">
        <defs><linearGradient id="lp-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="currentColor" stop-opacity=".16"/><stop offset="1" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs>
        <path class="lp-grid-line" d="M0 25H480M0 75H480M0 125H480"/>
        <path fill="url(#lp-area)" d="M5 30 65 45 120 39 185 70 245 63 305 95 370 89 430 112 475 121V150H5Z"/>
        <path class="lp-trend-line" d="m5 30 60 15 55-6 65 31 60-7 60 32 65-6 60 23 45 9"/>
        <circle cx="475" cy="121" r="5" fill="currentColor"/>
      </svg>
      <div class="lp-chart-labels"><span>开始记录</span><span>持续观察</span><span>看见变化</span></div>
      <div class="lp-preview-week"><span>一周有安排</span><div><span v-for="(day, i) in days" :key="day" :class="{ 'is-training': [0, 2, 4].includes(i) }">{{ day }}</span></div></div>
    </div>
    <figcaption>功能与数据为展示示意，实际计划与结果因人而异。</figcaption>
  </figure>
</template>
