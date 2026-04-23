from typing import TYPE_CHECKING

from django.contrib.auth.models import BaseUserManager

if TYPE_CHECKING:
    from accounts.models import User
    from tenancy.models import Tenant


class UserManager(BaseUserManager["User"]):
    def create_user(
        self,
        email: str,
        password: str,
        tenant: "Tenant",
        role: str,
        **extra: object,
    ) -> "User":
        if not email:
            raise ValueError("email required")
        email = self.normalize_email(email)
        user = self.model(email=email, tenant=tenant, role=role, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user
