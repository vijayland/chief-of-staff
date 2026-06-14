from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from app.dependencies import DBSession, require_admin
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.memory_node import MemoryNode

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/tenants")
async def list_tenants(db: DBSession, _: User = Depends(require_admin)):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    return [{"id": str(t.id), "name": t.name, "slug": t.slug, "plan": t.plan, "is_active": t.is_active} for t in tenants]


@router.get("/stats")
async def platform_stats(db: DBSession, _: User = Depends(require_admin)):
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    total_tenants = (await db.execute(select(func.count(Tenant.id)))).scalar()
    total_memories = (await db.execute(select(func.count(MemoryNode.id)))).scalar()
    return {
        "total_users": total_users,
        "total_tenants": total_tenants,
        "total_memories": total_memories,
    }


@router.patch("/tenants/{tenant_id}/suspend")
async def suspend_tenant(tenant_id: str, db: DBSession, _: User = Depends(require_admin)):
    import uuid
    result = await db.execute(select(Tenant).where(Tenant.id == uuid.UUID(tenant_id)))
    tenant = result.scalar_one_or_none()
    if not tenant:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Tenant")
    tenant.is_active = False
    return {"message": f"Tenant {tenant.name} suspended"}
