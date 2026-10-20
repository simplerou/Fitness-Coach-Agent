<script setup lang="ts">
import { ref } from 'vue'
import { CIRCUMFERENCES, SHAPE_LABELS } from '@/constants/shaping'
import type { ShapeCircumference } from '@/api/types'
const selected = ref<ShapeCircumference>('waist_cm')
const guides: Record<ShapeCircumference, { y: number; x1: number; x2: number; text: string }> = {
  waist_cm: { y: 139, x1: 84, x2: 136, text: '腰围：最低肋骨下缘与髂嵴上缘之间的中点，软尺水平绕一周。自然呼气末读数，不收腹。' },
  hip_cm: { y: 174, x1: 74, x2: 146, text: '臀围：双脚并拢站立，经过臀部向后最突出的位置，保持软尺水平。' },
  chest_cm: { y: 105, x1: 77, x2: 143, text: '胸围：经过胸部最丰满处（通常乳头水平），双臂自然下垂，平静呼吸，记录衣着条件。' },
  arm_cm: { y: 118, x1: 55, x2: 78, text: '臂围：固定测右臂（正面图的左侧）。找肩峰到肘尖的中点，手臂放松下垂，在中点垂直绕臂一周，不屈臂用力。' },
  thigh_cm: { y: 215, x1: 78, x2: 105, text: '腿围：固定测右腿（正面图的左侧）。取腹股沟褶皱到髌骨上缘的中点，站立、重心均匀，在该处水平测量。' },
}
</script>

<template>
  <details class="shape-guide" open>
    <summary>怎么量才更可比？查看测量位置</summary>
    <div class="shape-guide-layout">
      <svg viewBox="0 0 220 320" role="img" :aria-label="guides[selected].text">
        <circle cx="110" cy="35" r="22" fill="#e4eee6" stroke="#8ba395" />
        <path d="M99 57 L98 70 Q77 72 69 88 L45 158 Q42 171 51 174 Q59 177 64 165 L82 120 L83 148 Q67 171 76 194 L79 282 Q78 295 93 296 L106 206 L114 206 L127 296 Q142 296 141 282 L144 194 Q153 172 137 148 L138 120 L156 165 Q161 178 169 174 Q178 170 175 158 L151 88 Q143 72 122 70 L121 57" fill="#edf3ee" stroke="#8ba395" stroke-width="2" />
        <g stroke="#b8cabb" stroke-dasharray="3 3"><line x1="80" y1="129" x2="140" y2="129" /><line x1="79" y1="150" x2="141" y2="150" /></g>
        <line :x1="guides[selected].x1" :x2="guides[selected].x2" :y1="guides[selected].y" :y2="guides[selected].y" stroke="#176344" stroke-width="5" stroke-linecap="round" />
        <text x="110" y="315" text-anchor="middle" fill="#718079" font-size="10">示意图 · 位置按本人骨性标志定位</text>
      </svg>
      <div><div class="shape-switches"><button v-for="metric in CIRCUMFERENCES" :key="metric" class="button button-quiet" :aria-pressed="selected === metric" @click="selected = metric">{{ SHAPE_LABELS[metric] }}</button></div><p class="shape-guide-instruction">{{ guides[selected].text }}</p><ul class="shape-guide-tips"><li>使用无弹性软尺，贴合皮肤，不压出凹痕。</li><li>尽量同一时段、同一侧、同样衣着，不在刚训练后测量。</li><li>每处测两次取平均；相差超过 1 cm 时重测一次。小幅波动可能来自误差。</li></ul></div>
    </div>
  </details>
</template>
