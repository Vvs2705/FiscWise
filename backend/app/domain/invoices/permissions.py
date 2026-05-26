from fastapi import HTTPException, status
from app.models.user import User, UserRole

def verify_invoice_permission(current_user: User, action: str) -> None:
    """RBAC validation for sensitive actions in the invoices domain."""
    if action in ("create_issuer", "cancel_invoice"):
        if current_user.role.value not in (UserRole.OWNER.value, UserRole.ADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners and admins can perform this action"
            )
