"""Read-only account administration; authorization is checked against the database per request."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select

from ..database import AccountUserRecord, Base
from ..models import coach, shaping, shaping_intelligence, training_intelligence  # noqa: F401
from ..models.shaping import ShapePhotoRecord
from ..models.training_intelligence import ExerciseLibraryRecord

DATASETS = {
    "local_profiles": "建档信息", "body_profiles": "身体档案",
    "body_weight_history": "体重历史", "daily_signals": "每日状态",
    "training_preferences": "训练偏好", "training_schedule_preferences": "训练日安排",
    "weekly_plans": "周计划", "training_logs": "训练日志",
    "training_exercise_entries": "动作训练明细", "recovery_checkins": "恢复打卡",
    "exercise_advice": "动作进阶建议", "plan_adjustments": "计划调整",
    "diet_profiles": "饮食档案", "diet_meals": "餐食记录",
    "daily_water_intakes": "饮水记录", "diet_day_reviews": "饮食完整性",
    "diet_plan_snapshots": "饮食规划历史", "diet_day_adjustment": "每日饮食调整",
    "shape_measurements": "围度与体成分", "shape_targets": "塑形目标",
    "shape_photos": "体测照片", "shaping_intelligence_preferences": "塑形偏好",
    "muscle_group_stats": "肌群统计", "weak_part_advice": "薄弱部位建议",
    "qa_log": "教练问答", "coach_action_drafts": "教练草案",
    "report_snapshot": "分析报告", "local_safety_state": "安全暂停状态",
}
EXCLUDED_FIELDS = {"password_hash", "password_salt", "image_data", "user_id"}


def account_info(user):
    return {"id": user.id, "username": user.username, "display_name": user.display_name,
            "is_admin": user.is_admin, "created_at": user.created_at}


def create_admin_dependency(authenticate, session_factory):
    def require_admin(response: Response, user_id: int = Depends(authenticate)):
        with session_factory() as db:
            user = db.get(AccountUserRecord, user_id)
            if user is None:
                raise HTTPException(401, "登录状态已失效，请重新登录。")
            if not user.is_admin:
                raise HTTPException(403, "仅管理员可查看用户管理信息。")
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Vary"] = "Cookie"
        return user_id

    return require_admin


def create_admin_router(authenticate, session_factory):
    router = APIRouter(prefix="/api/admin", tags=["管理员"])

    require_admin = create_admin_dependency(authenticate, session_factory)

    def find_user(db, user_id):
        user = db.get(AccountUserRecord, user_id)
        if user is None:
            raise HTTPException(404, "未找到该用户。")
        return user

    @router.get("/users")
    def users(q: str = Query(default="", max_length=100),
              page: int = Query(default=1, ge=1),
              page_size: int = Query(default=20, ge=1, le=100),
              admin_id: int = Depends(require_admin)):
        query = select(AccountUserRecord)
        keyword = q.strip()
        if keyword:
            pattern = "%" + keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            query = query.where(or_(
                AccountUserRecord.username.ilike(pattern, escape="\\"),
                AccountUserRecord.display_name.ilike(pattern, escape="\\")))
        with session_factory() as db:
            total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
            rows = db.scalars(query.order_by(AccountUserRecord.id.desc())
                              .offset((page - 1) * page_size).limit(page_size)).all()
            return {"items": [account_info(user) for user in rows], "total": total,
                    "page": page, "page_size": page_size}

    @router.get("/users/{user_id}")
    def detail(user_id: int, admin_id: int = Depends(require_admin)):
        with session_factory() as db:
            user = find_user(db, user_id)
            datasets = []
            for key, label in DATASETS.items():
                table = Base.metadata.tables[key]
                count = db.scalar(select(func.count()).select_from(table)
                                  .where(table.c.user_id == user_id)) or 0
                datasets.append({"key": key, "label": label, "count": count})
            return {"user": account_info(user), "datasets": datasets}

    @router.get("/users/{user_id}/records/{dataset}")
    def records(user_id: int, dataset: str,
                page: int = Query(default=1, ge=1),
                page_size: int = Query(default=20, ge=1, le=100),
                admin_id: int = Depends(require_admin)):
        if dataset not in DATASETS:
            raise HTTPException(404, "不支持查看此类记录。")
        table = Base.metadata.tables[dataset]
        columns = [column for column in table.c if column.name not in EXCLUDED_FIELDS]
        query = select(*columns).where(table.c.user_id == user_id)
        dates = [name for name in ("recorded_on", "training_date", "checkin_date", "log_date",
                                  "signal_date", "week_start", "generated_on", "created_at",
                                  "adjustment_date", "updated_at") if name in table.c]
        order = [table.c[name].desc() for name in dates[:1]]
        order += [column.desc() for column in table.primary_key if column.name != "user_id"]
        with session_factory() as db:
            find_user(db, user_id)
            total = db.scalar(select(func.count()).select_from(table)
                              .where(table.c.user_id == user_id)) or 0
            rows = db.execute(query.order_by(*order).offset((page - 1) * page_size)
                              .limit(page_size)).mappings().all()
            names = dict(db.execute(select(ExerciseLibraryRecord.id, ExerciseLibraryRecord.name)).all())
            return {"items": [dict(row) for row in rows], "columns": [c.name for c in columns],
                    "exercise_names": {str(key): value for key, value in names.items()},
                    "total": total, "page": page, "page_size": page_size}

    @router.get("/users/{user_id}/photos/{photo_id}")
    def photo(user_id: int, photo_id: int, admin_id: int = Depends(require_admin)):
        with session_factory() as db:
            find_user(db, user_id)
            row = db.scalar(select(ShapePhotoRecord).where(
                ShapePhotoRecord.id == photo_id, ShapePhotoRecord.user_id == user_id))
            if row is None:
                raise HTTPException(404, "未找到该用户的照片。")
            return Response(row.image_data, media_type="image/jpeg",
                            headers={"Cache-Control": "private, no-store", "Vary": "Cookie",
                                     "X-Content-Type-Options": "nosniff"})
    return router
