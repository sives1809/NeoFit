"""
routers/validate.py  (Phase 5 stub)
--------------------------------------
GET  /validate/stats         Return MAE, RMSE, R² over validation_samples
POST /validate/sample        Add a ground-truth tape measurement paired with a session
"""

from fastapi import APIRouter
from app.dependencies import CurrentUser, DB

router = APIRouter(prefix="/validate", tags=["validate"])


@router.get("/stats")
async def validation_stats(user: CurrentUser, db: DB) -> dict:
    """
    Phase 5 — Compute and return accuracy metrics over the validation_samples table.
    """
    # TODO (Phase 5):
    # SELECT AVG(ABS(error_arm_cm)), SQRT(AVG(error_arm_cm^2)), etc.
    return {"status": "not_implemented", "message": "Implemented in Phase 5."}


@router.post("/sample")
async def add_validation_sample(body: dict, user: CurrentUser, db: DB) -> dict:
    """
    Phase 5 — Add a ground-truth tape measurement for academic validation.
    body: {session_id, tape_arm_cm, tape_thigh_cm, tape_shoulder_cm}
    """
    # TODO (Phase 5): join with session, compute errors, insert to validation_samples
    return {"status": "not_implemented", "message": "Implemented in Phase 5."}
