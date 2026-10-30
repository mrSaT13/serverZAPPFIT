"""Nutrition router — meal diary + OFF proxy + optional wger sync scaffold."""

from collections.abc import Callable
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import auth.dependencies as auth_dependencies
import core.cryptography as core_cryptography
import core.database as core_database
import core.logger as core_logger
import nutrition.ai as nutrition_ai
import nutrition.crud as nutrition_crud
import nutrition.models as nutrition_models
import nutrition.off_client as off_client
import nutrition.schema as nutrition_schema

router = APIRouter()


@router.get("", response_model=list[nutrition_schema.MealLogRead])
async def list_logs(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
) -> list[nutrition_schema.MealLogRead]:
    rows = nutrition_crud.list_meal_logs(token_user_id, date_from, date_to, db)
    return [nutrition_schema.MealLogRead.model_validate(r) for r in rows]


@router.post("", response_model=nutrition_schema.MealLogRead, status_code=status.HTTP_201_CREATED)
async def create_log(
    payload: nutrition_schema.MealLogCreate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> nutrition_schema.MealLogRead:
    row = nutrition_crud.create_meal_log(token_user_id, payload, db)
    return nutrition_schema.MealLogRead.model_validate(row)


@router.put("/{log_id}", response_model=nutrition_schema.MealLogRead)
async def update_log(
    log_id: int,
    payload: nutrition_schema.MealLogCreate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> nutrition_schema.MealLogRead:
    upd = nutrition_schema.MealLogUpdate(id=log_id, **payload.model_dump())
    row = nutrition_crud.update_meal_log(token_user_id, upd, db)
    return nutrition_schema.MealLogRead.model_validate(row)


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log(
    log_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> None:
    nutrition_crud.delete_meal_log(token_user_id, log_id, db)


@router.get("/favorites", response_model=list[nutrition_schema.FoodFavorite])
async def favorite_foods(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
    query: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=25)] = 8,
) -> list[nutrition_schema.FoodFavorite]:
    """Repeat-food suggestions from the user's own log history.

    Latest values per product name, most recent first. Stateless view —
    offline clients use their local log history instead.
    """
    rows = nutrition_crud.recent_foods(token_user_id, query, limit, db)
    return [nutrition_schema.FoodFavorite.model_validate(r) for r in rows]


@router.get("/summary", response_model=nutrition_schema.NutritionSummary)
async def summary(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
    target_date: Annotated[str | None, Query(alias="date")] = None,
) -> nutrition_schema.NutritionSummary:
    d = target_date or str(date.today())
    agg = nutrition_crud.summary_for_date(token_user_id, d, db)

    # Burned calories from activities on that date
    burned = 0.0
    try:
        from sqlalchemy import func as _func

        import activities.activity.models as _act_models

        # activities.calories is int (kcal) per activity.
        # func.date() yields a date — compare it to a date, not a string
        # (Postgres refuses `date = varchar`).
        d_date = date.fromisoformat(d)
        stmt = select(_func.coalesce(_func.sum(_act_models.Activity.calories), 0)).where(
            _act_models.Activity.user_id == token_user_id,
            _func.date(_act_models.Activity.start_time) == d_date,
        )
        burned = float(db.execute(stmt).scalar() or 0)
    except Exception:
        burned = 0.0

    # BMR Mifflin-St Jeor from users + latest weight
    bmr = 0.0
    try:
        from datetime import date as _date

        import health.health_weight.crud as _weight_crud
        import users.users.models as _users_models

        user = db.get(_users_models.Users, token_user_id)
        if user:
            # weight: prefer latest health_weight, else user weight implicit
            latest_weight = _weight_crud.get_latest_weight_by_user_id(token_user_id, db)
            weight_kg = float(latest_weight.weight) if latest_weight else None
            height_cm = user.height
            gender = (user.gender or "male").lower()
            # age from birthdate
            age = None
            if user.birthdate:
                today_d = _date.today()
                age = (
                    today_d.year
                    - user.birthdate.year
                    - ((today_d.month, today_d.day) < (user.birthdate.month, user.birthdate.day))
                )
            if weight_kg and height_cm and age is not None:
                s = 5 if gender == "male" else (-161 if gender == "female" else 0)
                bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + s
                if bmr < 0:
                    bmr = 0.0
    except Exception:
        bmr = 0.0

    total_burned = burned + bmr if (burned or bmr) else None
    net = None
    if total_burned is not None:
        net = float(agg["calories"] or 0) - float(total_burned)
    elif agg["calories"]:
        net = float(agg["calories"])

    return nutrition_schema.NutritionSummary(
        date=date.fromisoformat(d),
        intake_calories=agg["calories"],
        intake_protein=agg["protein"],
        intake_carbs=agg["carbs"],
        intake_fat=agg["fat"],
        burned_calories=total_burned,
        net_calories=net,
    )


@router.get("/trend", response_model=nutrition_schema.NutritionTrend)
async def trend(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
) -> nutrition_schema.NutritionTrend:
    """Per-day intake (+ burned) totals for the nutrition page charts.

    Defaults to the last 30 days; the range is capped at 366 days so a single
    client request can never scan the whole diary.
    """
    today = date.today()
    end_d = date.fromisoformat(date_to) if date_to else today
    start_d = date.fromisoformat(date_from) if date_from else end_d - timedelta(days=29)
    if start_d > end_d:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="date_from must be <= date_to")
    if (end_d - start_d).days > 366:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Date range must not exceed 366 days")

    totals = nutrition_crud.daily_totals(token_user_id, start_d.isoformat(), end_d.isoformat(), db)
    points = {
        row["date"]: nutrition_schema.NutritionTrendPoint(
            date=row["date"],
            calories=row["calories"],
            protein=row["protein"],
            carbs=row["carbs"],
            fat=row["fat"],
        )
        for row in totals
    }

    # Burned calories per day from activities (best-effort, mirrors /summary).
    try:
        from sqlalchemy import func as _func

        import activities.activity.models as _act_models

        stmt = (
            select(
                _func.date(_act_models.Activity.start_time).label("day"),
                _func.coalesce(_func.sum(_act_models.Activity.calories), 0),
            )
            .where(
                _act_models.Activity.user_id == token_user_id,
                _func.date(_act_models.Activity.start_time) >= start_d,
                _func.date(_act_models.Activity.start_time) <= end_d,
            )
            .group_by(_func.date(_act_models.Activity.start_time))
        )
        for day, kcal in db.execute(stmt).all():
            point = points.get(day)
            if point is None:
                point = nutrition_schema.NutritionTrendPoint(date=day)
                points[day] = point
            point.burned_calories = float(kcal or 0)
    except Exception:
        core_logger.print_to_log("Nutrition trend: burned-per-day aggregation failed", "error")

    ordered = [points[d] for d in sorted(points)]
    return nutrition_schema.NutritionTrend(date_from=start_d, date_to=end_d, days=ordered)


@router.get("/off/search", response_model=list[nutrition_schema.OffSearchResult])
async def off_search(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:read"])],
    q: Annotated[str, Query(min_length=2, max_length=100)],
    language: Annotated[str | None, Query(max_length=35)] = None,
) -> list[nutrition_schema.OffSearchResult]:
    try:
        results = await off_client.search_off(q, language=language or "en")
        return [nutrition_schema.OffSearchResult(**r) for r in results]
    except Exception as e:
        core_logger.print_to_log(f"OFF search error: {e}", "error", exc=e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OFF search failed") from e


@router.get("/off/product/{barcode}", response_model=nutrition_schema.OffSearchResult)
async def off_product(
    barcode: str,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:read"])],
) -> nutrition_schema.OffSearchResult:
    try:
        prod = await off_client.get_product(barcode)
        if not prod:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found in OFF")
        return nutrition_schema.OffSearchResult(**prod)
    except HTTPException:
        raise
    except Exception as e:
        core_logger.print_to_log(f"OFF product error: {e}", "error", exc=e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="OFF product fetch failed") from e


# --- wger scaffold ---
@router.get("/wger/settings", response_model=nutrition_schema.WgerSettingsRead)
async def get_wger_settings(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> nutrition_schema.WgerSettingsRead:
    stmt = select(nutrition_models.UserNutritionSettings).where(
        nutrition_models.UserNutritionSettings.user_id == token_user_id
    )
    row = db.scalars(stmt).first()
    if not row:
        return nutrition_schema.WgerSettingsRead()
    return nutrition_schema.WgerSettingsRead(
        wger_base_url=row.wger_base_url, wger_enabled=row.wger_enabled, has_api_key=bool(row.wger_api_key)
    )


@router.put("/wger/settings", response_model=nutrition_schema.WgerSettingsRead)
async def put_wger_settings(
    payload: nutrition_schema.WgerSettingsUpdate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> nutrition_schema.WgerSettingsRead:
    stmt = select(nutrition_models.UserNutritionSettings).where(
        nutrition_models.UserNutritionSettings.user_id == token_user_id
    )
    row = db.scalars(stmt).first()
    if not row:
        row = nutrition_models.UserNutritionSettings(user_id=token_user_id)
        db.add(row)
    row.wger_base_url = payload.wger_base_url
    row.wger_enabled = payload.wger_enabled
    if payload.wger_api_key:
        row.wger_api_key = core_cryptography.encrypt_token_fernet(payload.wger_api_key)
    elif payload.wger_api_key == "":
        row.wger_api_key = None
    db.commit()
    db.refresh(row)
    return nutrition_schema.WgerSettingsRead(
        wger_base_url=row.wger_base_url, wger_enabled=row.wger_enabled, has_api_key=bool(row.wger_api_key)
    )


@router.post("/wger/test", response_model=dict[str, str])
async def test_wger(
    payload: nutrition_schema.WgerTestRequest,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> dict[str, str]:
    import httpx

    # Explicit token wins; otherwise reuse the stored (encrypted) one so the
    # integration card can re-test without re-entering the token.
    api_key = payload.wger_api_key
    if not api_key:
        stmt = select(nutrition_models.UserNutritionSettings).where(
            nutrition_models.UserNutritionSettings.user_id == token_user_id
        )
        row = db.scalars(stmt).first()
        api_key = core_cryptography.decrypt_token_fernet(row.wger_api_key) if row and row.wger_api_key else None
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No wger API key provided or saved",
        )

    url = payload.wger_base_url.rstrip("/") + "/api/v2/nutrition/"
    headers = {"Authorization": f"Token {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                return {"message": "wger connection OK"}
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=f"wger returned {r.status_code}: {r.text[:200]}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"wger test failed: {e}") from e


# --- AI assistant ---
@router.get("/ai/status", response_model=nutrition_schema.AiStatusRead)
async def ai_status(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:read"])],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> nutrition_schema.AiStatusRead:
    """Tell the UI whether the AI nutrition assistant is available."""
    settings = nutrition_ai.get_ai_settings(db)
    return nutrition_schema.AiStatusRead(
        enabled=settings.enabled,
        configured=settings.configured,
        model=settings.model,
    )


@router.post("/ai/chat", response_model=nutrition_schema.AiChatReply)
async def ai_chat(
    payload: nutrition_schema.AiChatRequest,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["nutrition:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> nutrition_schema.AiChatReply:
    """Answer a nutrition question grounded in the user's own data.

    Stateless: the client sends the recent chat window; the server rebuilds
    the read-only data snapshot on every call and never stores the
    conversation.
    """
    settings = nutrition_ai.get_ai_settings(db)
    if not settings.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant is not configured. Ask your server administrator to enable it in server settings.",
        )

    context = nutrition_ai.build_context(db, token_user_id)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": nutrition_ai.system_prompt(payload.language)},
        {"role": "system", "content": f"User data snapshot:\n{context}"},
    ]
    messages += [{"role": m.role, "content": m.content} for m in payload.messages]

    try:
        reply = await nutrition_ai.chat_completion(settings.base_url, settings.api_key, settings.model, messages)
    except nutrition_ai.AiAssistantError as e:
        core_logger.print_to_log(f"AI chat error: {e}", "error", exc=e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
    return nutrition_schema.AiChatReply(reply=reply, model=settings.model)
