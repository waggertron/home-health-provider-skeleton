"""REST entry point for enqueuing a VRP optimize.

POST /api/v1/schedule/<date>/optimize fires scheduling.optimize_day for
the caller's tenant and returns {job_id, status} immediately. Polling
(Phase 4) will go through the Celery result backend.
"""

from __future__ import annotations

from datetime import date as _date

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsSchedulerOrAdmin
from scheduling.tasks import optimize_day


class OptimizeDayView(APIView):
    permission_classes = [IsAuthenticated, IsSchedulerOrAdmin]

    def post(self, request: Request, iso_date: str) -> Response:
        try:
            target = _date.fromisoformat(iso_date)
        except ValueError:
            return Response(
                {"detail": "Malformed date — expected YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tenant_id = request.user.tenant_id
        async_result = optimize_day.delay(tenant_id, target.isoformat())
        return Response(
            {"job_id": async_result.id, "status": async_result.status},
            status=status.HTTP_202_ACCEPTED,
        )
