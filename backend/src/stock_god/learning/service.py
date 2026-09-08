import json
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from stock_god.adapters.data import CONTENT
from stock_god.db.session import owner
from stock_god.trading.engine import get_account
from stock_god.db.models import Progress, Reward, Attempt, Player, Order, Reflection, Job, now
from stock_god.learning import reviews

LESSONS = json.loads((CONTENT / "courses" / "catalog.json").read_text(encoding="utf-8"))


def progress_id(session, lesson):
    return f"{owner(session)}:{lesson}:1"


def course(session, lesson_id):
    lesson = next((x for x in LESSONS if x["id"] == lesson_id), None)
    if lesson is None:
        raise HTTPException(404, "没有找到这节课，请回到学习地图。")
    progress = session.get(Progress, progress_id(session, lesson_id))
    locked = any(not (p := session.get(Progress, progress_id(session, prev))) or not p.completed for prev in lesson["prerequisites"])
    result = {k: v for k, v in lesson.items() if k != "questions"}
    result.update(version=1, locked=locked, completed=bool(progress and progress.completed),
                  review_due=any(r.lesson_id == lesson_id and reviews.is_due(r, now()) for r in reviews.entries(session)), attempts=progress.attempts if progress else 0,
                  last_score=progress.last_score if progress else 0)
    return result


def course_detail(session, lesson_id):
    result = course(session, lesson_id)
    if result["locked"]:
        raise HTTPException(409, "请先完成前置章节的独立练习，再解锁本课。")
    lesson = next(x for x in LESSONS if x["id"] == lesson_id)
    result["body"] = (CONTENT / "courses" / f"{lesson_id}.md").read_text(encoding="utf-8")
    result["questions"] = [{"prompt": q["prompt"], "options": q["options"]} for q in lesson["questions"]]
    return result


def evaluate(session, lesson_id, answers):
    detail = course_detail(session, lesson_id)
    lesson = next(x for x in LESSONS if x["id"] == lesson_id)
    if len(answers) != len(lesson["questions"]) or any(a < 0 or a >= len(q["options"]) for a, q in zip(answers, lesson["questions"])):
        raise HTTPException(422, "请完成每一道独立练习题后再提交。")
    feedback = [{"passed": a == q["correct"], "explanation": q["explanation"]} for a, q in zip(answers, lesson["questions"])]
    reviews.record_mistakes(session, lesson_id, feedback)
    score = round(sum(q["passed"] for q in feedback) / len(feedback) * 100)
    missing = []
    if lesson_id == "orders" and not session.scalar(select(Order).where(Order.account_id == get_account(session, "tutorial").id, Order.status == "filled")):
        missing.append("请先在教学账户完成一次模拟成交，并查看处理结果。")
    if lesson_id == "risk" and not session.scalar(select(Reflection).where(Reflection.player_id == owner(session), Reflection.account_id == get_account(session, "tutorial").id)):
        missing.append("请先保存一份交易计划与复盘。")
    if lesson_id == "strategy" and not session.scalar(select(Job).where(Job.player_id == owner(session), Job.status == "completed")):
        missing.append("请先完成一次教学策略实验。")
    passed = score == 100 and not missing
    p = session.get(Progress, progress_id(session, lesson_id))
    if p is None:
        p = Progress(id=progress_id(session, lesson_id), lesson_id=lesson_id, player_id=owner(session), attempts=0, completed=False)
        session.add(p)
    p.attempts += 1
    p.last_score, p.review_due, p.updated_at = score, score < 100, now()
    p.completed = p.completed or passed
    award = 0
    if passed and not session.get(Reward, progress_id(session, lesson_id)):
        award = lesson["xp"]
        session.add(Reward(id=progress_id(session, lesson_id), lesson_id=lesson_id, player_id=owner(session), xp=award, badge=lesson["badge"]))
        session.get(Player, owner(session)).xp += award
    session.add(Attempt(id=str(uuid4()), lesson_id=lesson_id, player_id=owner(session), answers=answers, score=score, feedback=feedback))
    session.flush()
    return {"passed": passed, "score": score, "feedback": feedback, "requirements": missing, "xp_awarded": award,
            "message": "独立练习已完成，下一章节已解锁。" if passed else "请根据讲解补全练习，再试一次。", "lesson_id": lesson_id}

