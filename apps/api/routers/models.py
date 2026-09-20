"""Model Registry and Quality Gating Router.

Implements:
- GET /api/models & GET /models
- GET /api/models/{id} & GET /models/{id}
- GET /api/models/{id}/metrics & GET /models/{id}/metrics
- POST /api/models/{id}/gate
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException

from packages.scenario_engine.registry.model_registry import global_model_registry

router = APIRouter(tags=["models"])


@router.get("/models")
@router.get("/api/models")
async def list_registered_models():
    """Retrieve all models in registry with versions, status, and gating outcomes."""
    models = global_model_registry.list_models()
    return {
        "status": "ok",
        "total_models": len(models),
        "active_models_count": len([m for m in models if m.get("status") == "ACTIVE"]),
        "models": models,
    }


@router.get("/models/{id}")
@router.get("/api/models/{id}")
async def get_model_details(id: str):
    """Retrieve specific model architecture, version, and gating report."""
    model = global_model_registry.get_model(id)
    if not model:
        # Match case-insensitively or return first matching
        for m in global_model_registry.list_models():
            if id.lower() in m["model_id"].lower() or id.lower() in m["model_name"].lower():
                return m
        raise HTTPException(status_code=404, detail=f"Model '{id}' not found in registry")
    return model


@router.get("/models/{id}/metrics")
@router.get("/api/models/{id}/metrics")
async def get_model_metrics(id: str):
    """Retrieve detailed out-of-sample metrics, Brier scores, and calibration curve for model."""
    model = global_model_registry.get_model(id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{id}' not found")

    return {
        "model_id": model["model_id"],
        "model_name": model["model_name"],
        "status": model["status"],
        "metrics": model.get("metrics", {}),
        "gating_passed": model.get("gating_passed", True),
        # Calibration deciles require an evaluated out-of-sample run; none is
        # persisted, so none is served.
        "calibration_deciles": [],
        "note": "Calibration deciles are populated only after an out-of-sample evaluation run is persisted for this model.",
    }


@router.post("/models/{id}/gate")
@router.post("/api/models/{id}/gate")
async def gate_model(id: str):
    """Run empirical gating checks on a model (§19)."""
    try:
        updated = global_model_registry.evaluate_and_gate(id)
        return updated
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Model '{id}' not found")
