"""API v1 router assembly."""

from fastapi import APIRouter
from backend.api.v1.agent import router as agent_router
from backend.api.v1.approvals import router as approvals_router
from backend.api.v1.audit import router as audit_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.certificates import router as certs_router
from backend.api.v1.devices import router as devices_router
from backend.api.v1.jobs import router as jobs_router
from backend.api.v1.public import router as public_router
from backend.api.v1.reports import router as reports_router
from backend.api.v1.users import router as users_router
from backend.api.v1.wipe_requests import router as requests_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(devices_router)
api_v1_router.include_router(agent_router)
api_v1_router.include_router(requests_router)
api_v1_router.include_router(approvals_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(certs_router)
api_v1_router.include_router(public_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(reports_router)

__all__ = ["api_v1_router"]
