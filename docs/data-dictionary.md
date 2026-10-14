# 数据字典占位

详细字段待按规划书第 7 章落地。核心实体：`user_profile`、`injury_history`、`consent_record`、`daily_signal`、`training_log`、`training_plan`、`safety_hold`、`coach_annotation`、`daily_load`、`override_event`。

缺失、过期、异常值与明确零值必须区分；每条状态信号需记录来源、采集时间和有效性。健康数据表结构变更需通过 Alembic 迁移。
