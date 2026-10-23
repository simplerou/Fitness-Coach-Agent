<script setup lang="ts">
import ProductPreview from '@/components/landing/ProductPreview.vue'
import '@/styles/landing.css'
const emit = defineEmits<{ authenticate: [mode: 'login' | 'register'] }>()
const features = [
  { n: '01', title: '训练，有计划可循', text: '结合目标、经验、器械与可用时间安排一周训练，把计划和每一次执行放在一起。', tag: '周计划 / 训练记录', icon: 'M5 8v8m3-11v14m8-14v14m3-11v8M8 12h8' },
  { n: '02', title: '饮食，和训练一起安排', text: '规划餐食、记录摄入与饮水，参考训练日和休息日建议，让每天吃什么更有依据。', tag: '饮食规划 / 营养目标', icon: 'M5 3v6a3 3 0 0 0 6 0V3M8 3v18M19 3c-4 3-4 9 0 9v9m0-18v9' },
  { n: '03', title: '变化，不只看体重', text: '把围度、体脂、骨骼肌与对比照放进时间线，从多个角度观察自己的变化。', tag: '体测追踪 / 周月报告', icon: 'M4 19V5m0 14h16M8 14l4-5 4 2 4-6' },
  { n: '04', title: '有疑问，问问 AI 教练', text: '查动作要领、了解替代动作、结合记录回顾表现；需要调整时，先看建议，再由你确认。', tag: '动作检索 / 上下文问答', icon: 'M5 4h14v12H9l-4 4V4Zm4 5h6m-6 3h4' },
]
const steps = [
  { title: '认识你的起点', text: '填写身体档案、目标与训练偏好。' },
  { title: '安排下一步', text: '制定可执行的训练与饮食计划。' },
  { title: '记录每次行动', text: '留下训练、饮食和身体变化。' },
  { title: '回顾，再做调整', text: '结合趋势与建议，安排下一阶段。' },
]
function goTo(id: string): void {
  document.getElementById(id)?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
  document.getElementById(id)?.focus({ preventScroll: true })
}
</script>

<template>
  <div class="landing-page">
    <a class="lp-skip" href="#lp-main" @click.prevent="goTo('lp-main')">跳至主要内容</a>
    <header class="lp-header"><div class="lp-container lp-nav">
      <a class="lp-brand" href="#" aria-label="青禾训练助理，回到顶部" @click.prevent="goTo('lp-main')"><span class="lp-brand-mark" aria-hidden="true">禾</span><span>青禾<small>训练助理</small></span></a>
      <nav aria-label="产品导航"><a href="#lp-features" @click.prevent="goTo('lp-features')">产品功能</a><a href="#lp-how" @click.prevent="goTo('lp-how')">如何开始</a></nav>
      <div class="lp-nav-actions"><button class="lp-button lp-button-quiet" @click="emit('authenticate', 'login')">登录</button><button class="lp-button lp-button-primary" @click="emit('authenticate', 'register')">注册 <span aria-hidden="true">↗</span></button></div>
    </div></header>
    <main id="lp-main" tabindex="-1">
      <section class="lp-container lp-hero" aria-labelledby="lp-title">
        <div class="lp-hero-copy"><p class="lp-eyebrow"><span/> 为每一次认真改变</p><h1 id="lp-title">练得有方向，<br>变化<span class="lp-title-accent">看得见。</span></h1><p class="lp-lead">让训练、饮食和身体变化连成一条线。<br class="lp-desktop-break">青禾陪你把减脂塑形，变成有计划的日常。</p><div class="lp-hero-actions"><button class="lp-button lp-button-primary lp-button-large" @click="emit('authenticate', 'login')">开始我的训练计划 <span aria-hidden="true">→</span></button><a class="lp-text-link" href="#lp-features" @click.prevent="goTo('lp-features')">先了解一下 <span aria-hidden="true">↓</span></a></div><p class="lp-hero-note">从你的目标出发，按自己的节奏前进。</p><div class="lp-hero-topics"><span>训练规划</span><span>饮食联动</span><span>效果追踪</span><span>AI 教练</span></div></div>
        <div class="lp-hero-visual"><div class="lp-visual-caption"><span>YOUR EVERYDAY PROGRESS</span><span>规划 · 行动 · 回顾</span></div><ProductPreview/><div class="lp-visual-footnote"><span class="lp-note-line"/><span>不必追求每天完美，让每一步有迹可循。</span></div></div>
      </section>
      <section class="lp-principle"><div class="lp-container"><p>少一点来回切换，多一点持续行动。</p><span>从制定计划到看见反馈，在同一个工作台完成。</span></div></section>
      <section id="lp-features" class="lp-container lp-section" tabindex="-1" aria-labelledby="lp-features-title"><div class="lp-section-heading"><div><p class="lp-eyebrow">ONE CONNECTED ROUTINE</p><h2 id="lp-features-title">你的日常，终于连在一起。</h2></div><p>不只是记录数字，<br>也让数字帮你找到下一步。</p></div><div class="lp-feature-grid"><article v-for="feature in features" :key="feature.n" class="lp-feature"><div class="lp-feature-top"><svg viewBox="0 0 24 24" aria-hidden="true"><path :d="feature.icon"/></svg><span>{{ feature.n }}</span></div><h3>{{ feature.title }}</h3><p>{{ feature.text }}</p><small>{{ feature.tag }}</small></article></div></section>
      <section id="lp-how" class="lp-how lp-section" tabindex="-1" aria-labelledby="lp-how-title"><div class="lp-container"><div class="lp-section-heading"><div><p class="lp-eyebrow">A LITTLE BETTER, EVERY WEEK</p><h2 id="lp-how-title">从了解自己，到找到节奏。</h2></div><p>不必一步到位，<br>先从一个可执行的计划开始。</p></div><ol class="lp-steps"><li v-for="(step, i) in steps" :key="step.title"><span class="lp-step-number">0{{ i + 1 }}</span><h3>{{ step.title }}</h3><p>{{ step.text }}</p></li></ol><p class="lp-expectation">变化需要时间，通常在 4–8 周逐渐显现。记录用于观察趋势，不代表效果承诺。</p></div></section>
      <section class="lp-container lp-closing" aria-labelledby="lp-closing-title"><div><p class="lp-eyebrow">从今天的一小步开始</p><h2 id="lp-closing-title">下一次改变，从有计划开始。</h2><p>把目标留给时间，把今天交给行动。</p></div><button class="lp-button lp-button-primary lp-button-large" @click="emit('authenticate', 'login')">建立我的训练档案 <span aria-hidden="true">→</span></button></section>
    </main>
    <footer class="lp-footer lp-container"><span>青禾训练助理 · 认真对待每一份坚持</span><span>训练与饮食建议仅供参考，不替代医疗建议。</span></footer>
  </div>
</template>
