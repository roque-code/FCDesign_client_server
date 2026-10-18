import math

from django.db.models import Q
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Profile, User
from apps.billing.models import Plan
from apps.billing.services import (
    assign_plan,
    catalog_payload,
    create_plan,
    plan_payload,
    update_plan,
    user_row,
)
from apps.http import current_user, object_body
from config.errors import DomainError


def _admin(request: Request) -> User:
    user = current_user(request)
    if user.profile.role != Profile.ADMIN:
        raise DomainError("Solo un administrador puede definir los niveles.", status_code=403)
    return user


class CatalogView(APIView):
    def get(self, request: Request) -> Response:
        _admin(request)
        return Response({"results": catalog_payload()})


class PlanListView(APIView):
    def get(self, request: Request) -> Response:
        _admin(request)
        return Response({"results": [plan_payload(plan) for plan in Plan.objects.all()]})

    def post(self, request: Request) -> Response:
        _admin(request)
        plan = create_plan(object_body(request.data))
        return Response(plan_payload(plan), status=201)


class PlanDetailView(APIView):
    def patch(self, request: Request, plan_id) -> Response:
        _admin(request)
        try:
            plan = Plan.objects.get(pk=plan_id)
        except (Plan.DoesNotExist, ValueError, TypeError) as exc:
            raise DomainError(
                "No se encontró el nivel.", code="not_found", status_code=404
            ) from exc
        return Response(plan_payload(update_plan(plan, object_body(request.data))))


def _page_number(value: object, default: int, upper: int | None = None) -> int:
    try:
        number = int(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        number = default
    if number < 1:
        number = 1
    if upper is not None and number > upper:
        number = upper
    return number


class SubscriberListView(APIView):
    page_size = 15

    def get(self, request: Request) -> Response:
        _admin(request)
        query = request.query_params.get("q", "")
        if not isinstance(query, str):
            query = ""
        text = query.strip()
        people = User.objects.select_related("profile").exclude(profile__role=Profile.ADMIN)
        if text:
            people = people.filter(
                Q(email__icontains=text) | Q(profile__display_name__icontains=text)
            )
        people = people.order_by("email")
        size = _page_number(request.query_params.get("page_size"), self.page_size, upper=50)
        total = people.count()
        pages = max(1, math.ceil(total / size))
        page = _page_number(request.query_params.get("page"), 1, upper=pages)
        start = (page - 1) * size
        rows = [user_row(user) for user in people[start : start + size]]
        return Response({"results": rows, "count": total, "page": page, "pages": pages})


class SubscriberDetailView(APIView):
    def patch(self, request: Request, user_id: int) -> Response:
        _admin(request)
        try:
            person = User.objects.select_related("profile").get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError) as exc:
            raise DomainError(
                "No se encontró la cuenta.", code="not_found", status_code=404
            ) from exc
        assign_plan(person, object_body(request.data))
        return Response(user_row(person))
