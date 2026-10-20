"""可重复执行的动作库种子数据。"""
from sqlalchemy import select

from ..models.training_intelligence import ExerciseLibraryRecord


def _exercise(slug: str, name: str, category: str, muscles: list[str], equipment: list[str],
              cues: list[str], errors: list[tuple[str, str]], regressions: list[str],
              progressions: list[str], alternatives: list[tuple[str, str]]) -> dict:
    return {
        "slug": slug, "name": name, "category": category, "target_muscles": muscles,
        "equipment": equipment, "cues": cues,
        "common_errors": [{"error": error, "correction": correction} for error, correction in errors],
        "regressions": regressions, "progressions": progressions,
        "alternatives": [{"name": name, "scene": scene} for name, scene in alternatives], "is_seed": True,
    }


SEED_EXERCISES = [
    _exercise("push-up", "俯卧撑", "胸", ["胸大肌", "肱三头肌"], ["bodyweight_only"], ["身体保持一条直线", "下放吸气，推起呼气"], [("塌腰", "收紧核心并缩短动作幅度"), ("手肘外展", "手肘与躯干约呈 45°")], ["跪姿俯卧撑", "墙面俯卧撑"], ["脚高手低俯卧撑"], [("哑铃卧推", "有哑铃"), ("弹力带胸推", "居家")]),
    _exercise("dumbbell-bench-press", "哑铃卧推", "胸", ["胸大肌", "肱三头肌"], ["dumbbells", "gym"], ["肩胛稳定贴住凳面", "前臂接近垂直"], [("肩部前顶", "收紧肩胛并降低重量"), ("下放过深", "在肩部舒适范围内停止")], ["地板哑铃卧推"], ["上斜哑铃卧推"], [("俯卧撑", "无器械"), ("器械推胸", "健身房")]),
    _exercise("incline-push-up", "上斜俯卧撑", "胸", ["胸大肌", "肱三头肌"], ["bodyweight_only"], ["双手支撑稳定高台", "胸口靠近支撑面"], [("耸肩", "肩膀远离耳朵"), ("髋部下沉", "收紧臀腹")], ["墙面俯卧撑"], ["标准俯卧撑"], [("弹力带胸推", "居家"), ("器械推胸", "健身房")]),
    _exercise("lat-pulldown", "高位下拉", "背", ["背阔肌", "肱二头肌"], ["gym"], ["先下沉肩胛再拉", "拉至锁骨附近并呼气"], [("身体后仰过多", "减轻重量并保持躯干稳定"), ("用手臂猛拉", "想象肘部向下靠近身体")], ["弹力带下拉"], ["引体向上"], [("弹力带下拉", "居家"), ("单臂哑铃划船", "有哑铃")]),
    _exercise("one-arm-row", "单臂哑铃划船", "背", ["背阔肌", "菱形肌"], ["dumbbells", "gym"], ["背部保持中立", "肘部向髋部方向拉"], [("转动躯干", "降低重量并固定骨盆"), ("耸肩", "肩胛向后下方移动")], ["弹力带坐姿划船"], ["俯身双臂划船"], [("坐姿划船", "健身房"), ("弹力带划船", "居家")]),
    _exercise("seated-row", "坐姿划船", "背", ["背阔肌", "菱形肌"], ["gym", "resistance_bands"], ["胸廓自然抬起", "肘部贴近身体后拉"], [("含胸", "减轻重量并保持脊柱中立"), ("借力后仰", "保持躯干基本不动")], ["弹力带划船"], ["单臂划船"], [("单臂哑铃划船", "有哑铃"), ("反向划船", "无器械")]),
    _exercise("squat", "徒手深蹲", "腿", ["股四头肌", "臀大肌"], ["bodyweight_only"], ["膝盖跟随脚尖方向", "起身时脚掌均匀发力"], [("膝盖内扣", "减小幅度并让膝盖对准脚尖"), ("脚跟离地", "调整站距并减少下蹲深度")], ["坐凳深蹲"], ["高脚杯深蹲"], [("腿举", "健身房"), ("高脚杯深蹲", "有哑铃")]),
    _exercise("goblet-squat", "高脚杯深蹲", "腿", ["股四头肌", "臀大肌"], ["dumbbells", "gym"], ["哑铃靠近胸前", "下蹲时保持躯干稳定"], [("重量远离身体", "让重量贴近胸口"), ("膝盖内扣", "降低重量并控制膝盖方向")], ["徒手深蹲"], ["双哑铃深蹲"], [("徒手深蹲", "无器械"), ("腿举", "健身房")]),
    _exercise("romanian-deadlift", "罗马尼亚硬拉", "腿", ["腘绳肌", "臀大肌"], ["dumbbells", "gym"], ["髋部向后移动", "重量贴近双腿"], [("弓背", "减轻重量并保持脊柱中立"), ("变成深蹲", "保持小腿相对竖直")], ["徒手髋铰链"], ["单腿罗马尼亚硬拉"], [("臀桥", "无器械"), ("绳索拉力", "健身房")]),
    _exercise("glute-bridge", "臀桥", "腿", ["臀大肌", "腘绳肌"], ["bodyweight_only", "resistance_bands"], ["脚跟靠近臀部", "顶端收紧臀部并呼气"], [("腰部过伸", "收紧腹部并减少顶起高度"), ("膝盖内扣", "保持膝盖朝向脚尖")], ["短幅臀桥"], ["单腿臀桥"], [("罗马尼亚硬拉", "有哑铃"), ("髋推", "健身房")]),
    _exercise("reverse-lunge", "反向箭步蹲", "腿", ["股四头肌", "臀大肌"], ["bodyweight_only", "dumbbells"], ["向后迈步并保持前脚稳定", "前腿发力站起"], [("前膝内扣", "让膝盖跟随脚尖"), ("步幅过窄", "略加宽左右间距")], ["扶墙反向箭步蹲"], ["哑铃反向箭步蹲"], [("分腿蹲", "小空间"), ("腿举", "健身房")]),
    _exercise("overhead-press", "哑铃推举", "肩", ["三角肌", "肱三头肌"], ["dumbbells", "gym"], ["肋骨保持稳定", "向上推时呼气"], [("腰部过伸", "减轻重量并收紧核心"), ("肩部耸起", "控制重量并保持颈部放松")], ["坐姿单臂推举"], ["站姿推举"], [("弹力带推举", "居家"), ("器械肩推", "健身房")]),
    _exercise("lateral-raise", "哑铃侧平举", "肩", ["三角肌中束"], ["dumbbells", "resistance_bands"], ["手肘微屈", "抬至肩部舒适高度"], [("耸肩", "减轻重量并让肩膀下沉"), ("借力摆动", "减轻重量并放慢速度")], ["单臂扶墙侧平举"], ["停顿侧平举"], [("弹力带侧平举", "居家"), ("绳索侧平举", "健身房")]),
    _exercise("face-pull", "面拉", "肩", ["三角肌后束", "上背"], ["resistance_bands", "gym"], ["拉向眉眼高度", "结束时双手分开"], [("耸肩", "肩胛向后下方移动"), ("腰部后仰", "减轻阻力并站稳")], ["弹力带拉开"], ["绳索面拉"], [("俯身反向飞鸟", "有哑铃"), ("弹力带拉开", "居家")]),
    _exercise("biceps-curl", "哑铃弯举", "臂", ["肱二头肌"], ["dumbbells", "resistance_bands"], ["上臂保持稳定", "弯举时呼气"], [("身体摆动", "减轻重量并靠墙完成"), ("手腕弯曲", "保持手腕中立")], ["交替弯举"], ["慢速离心弯举"], [("弹力带弯举", "居家"), ("绳索弯举", "健身房")]),
    _exercise("triceps-extension", "肱三头肌下压", "臂", ["肱三头肌"], ["resistance_bands", "gym"], ["上臂贴近身体", "伸直时呼气"], [("肘部前后移动", "减轻阻力并固定上臂"), ("含胸", "保持胸廓自然抬起")], ["弹力带下压"], ["单臂下压"], [("窄距俯卧撑", "无器械"), ("哑铃臂屈伸", "有哑铃")]),
    _exercise("plank", "平板支撑", "核心", ["腹横肌", "腹直肌"], ["bodyweight_only"], ["头髋脚保持一线", "保持自然呼吸"], [("塌腰", "缩短保持时间并收紧腹部"), ("抬头", "让颈部与脊柱保持中立")], ["跪姿平板支撑"], ["长杠杆平板支撑"], [("死虫", "腰部敏感"), ("Pallof 抗旋转", "有弹力带")]),
    _exercise("dead-bug", "死虫", "核心", ["腹横肌", "腹直肌"], ["bodyweight_only"], ["腰背自然贴地", "对侧手脚缓慢伸展"], [("腰部离地", "减小伸展幅度"), ("动作过快", "放慢速度并配合呼吸")], ["仅移动手臂或腿"], ["加负重死虫"], [("鸟狗", "俯卧支撑场景"), ("平板支撑", "静力训练")]),
    _exercise("bird-dog", "鸟狗", "核心", ["核心", "竖脊肌"], ["bodyweight_only"], ["保持骨盆水平", "对侧手脚向远处伸展"], [("腰部旋转", "减小抬起高度"), ("耸肩", "手臂向前延伸而非向上")], ["仅伸单腿"], ["停顿鸟狗"], [("死虫", "仰卧场景"), ("Pallof 抗旋转", "有弹力带")]),
    _exercise("pallof-press", "Pallof 抗旋转", "核心", ["腹斜肌", "腹横肌"], ["resistance_bands", "gym"], ["身体侧对拉力方向", "推出时保持躯干不旋转"], [("身体被拉转", "减轻阻力并缩短距离"), ("憋气", "推出时缓慢呼气")], ["跪姿短距离抗旋转"], ["半跪姿抗旋转"], [("死虫", "无器械"), ("绳索抗旋转", "健身房")]),
    _exercise("calf-raise", "提踵", "腿", ["腓肠肌", "比目鱼肌"], ["bodyweight_only", "dumbbells"], ["脚趾朝前并稳定站立", "顶端停顿后缓慢下放"], [("脚踝外翻", "扶稳支撑并减小幅度"), ("快速弹跳", "放慢离心阶段")], ["双脚扶墙提踵"], ["单腿提踵"], [("坐姿提踵", "健身房"), ("台阶提踵", "居家")]),
    _exercise("step-up", "台阶踏步", "腿", ["股四头肌", "臀大肌"], ["bodyweight_only", "dumbbells"], ["整只脚踩稳台阶", "前腿主导站起"], [("后脚蹬地过多", "降低台阶并放慢动作"), ("膝盖内扣", "让膝盖朝向脚尖")], ["低台阶扶墙踏步"], ["负重踏步"], [("反向箭步蹲", "无台阶"), ("腿举", "健身房")]),
    _exercise("band-pull-apart", "弹力带拉开", "背", ["三角肌后束", "上背"], ["resistance_bands"], ["手臂在胸前伸直", "肩胛向后靠拢"], [("耸肩", "肩膀远离耳朵"), ("腰部后仰", "减轻阻力并站稳")], ["更轻弹力带"], ["停顿拉开"], [("面拉", "有固定点"), ("反向飞鸟", "有哑铃")]),
    _exercise("mountain-climber", "登山跑", "核心", ["核心", "髋屈肌"], ["bodyweight_only"], ["双手稳定撑地", "膝盖交替向胸口移动"], [("臀部抬得过高", "放慢速度并保持躯干稳定"), ("肩部前后晃动", "缩小腿部动作幅度")], ["慢速登山步"], ["交叉登山跑"], [("死虫", "低冲击"), ("平板支撑", "静力训练")]),
]


MEDIA_BASE_URL = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises"
MEDIA_REPOSITORY_URL = "https://github.com/yuhonas/free-exercise-db"
EXERCISE_MEDIA_IDS = {
    "push-up": "Pushups",
    "dumbbell-bench-press": "Dumbbell_Bench_Press",
    "incline-push-up": "Incline_Push-Up",
    "lat-pulldown": "Wide-Grip_Lat_Pulldown",
    "one-arm-row": "One-Arm_Dumbbell_Row",
    "seated-row": "Seated_Cable_Rows",
    "squat": "Bodyweight_Squat",
    "goblet-squat": "Goblet_Squat",
    "romanian-deadlift": "Romanian_Deadlift",
    "glute-bridge": "Butt_Lift_Bridge",
    "reverse-lunge": "Dumbbell_Rear_Lunge",
    "overhead-press": "Seated_Dumbbell_Press",
    "lateral-raise": "Side_Lateral_Raise",
    "face-pull": "Face_Pull",
    "biceps-curl": "Dumbbell_Bicep_Curl",
    "triceps-extension": "Triceps_Pushdown",
    "plank": "Plank",
    "dead-bug": "Dead_Bug",
    "pallof-press": "Pallof_Press",
    "calf-raise": "Standing_Dumbbell_Calf_Raise",
    "step-up": "Dumbbell_Step_Ups",
    "band-pull-apart": "Band_Pull_Apart",
    "mountain-climber": "Mountain_Climbers",
}

for exercise in SEED_EXERCISES:
    media_id = EXERCISE_MEDIA_IDS.get(exercise["slug"])
    exercise.update({
        "demo_images": ([f"{MEDIA_BASE_URL}/{media_id}/0.jpg", f"{MEDIA_BASE_URL}/{media_id}/1.jpg"]
                        if media_id else []),
        "demo_video_url": None,
        "media_credit": "yuhonas/free-exercise-db contributors" if media_id else None,
        "media_license": "Unlicense / Public Domain" if media_id else None,
        "media_source_url": (f"{MEDIA_REPOSITORY_URL}/tree/main/exercises/{media_id}"
                             if media_id else None),
    })


def ensure_exercise_seed(db) -> int:
    existing = {row.slug: row for row in db.scalars(select(ExerciseLibraryRecord)).all()}
    added = 0
    for item in SEED_EXERCISES:
        row = existing.get(item["slug"])
        if row is None:
            db.add(ExerciseLibraryRecord(**item))
            added += 1
            continue
        # Seed enrichment is idempotent so existing installations receive new media metadata.
        for field in ("demo_images", "demo_video_url", "media_credit", "media_license", "media_source_url"):
            setattr(row, field, item[field])
    return added

