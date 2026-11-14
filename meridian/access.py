from django.http import Http404
from .audit import record
from .models import Astronaut, MissionAccess


class ScopeDenied(Exception):
    pass


def access_for(user):
    try:
        return user.mission_access
    except MissionAccess.DoesNotExist:
        return None


def permitted(user, astronaut_id=None, roles=None, write=False):
    access = access_for(user)
    # A superuser is an explicit local operator; generic staff status grants no mission scope.
    if user.is_superuser:
        return True
    if not access:
        return False
    if roles and access.role not in roles:
        return False
    if write and access.role not in {"astronaut", "medical_officer"}:
        return False
    if astronaut_id is not None:
        if access.role == "astronaut":
            return access.astronaut_id == astronaut_id
        return access.role in {"medical_officer", "flight_surgeon"}
    return True


def require_scope(user, astronaut_id=None, roles=None, write=False):
    if not permitted(user, astronaut_id, roles, write):
        record(user.pk, "access_denied", str(astronaut_id or ""), {"roles": roles or [], "write": write})
        raise ScopeDenied
    return Astronaut.objects.get(pk=astronaut_id) if astronaut_id else None
