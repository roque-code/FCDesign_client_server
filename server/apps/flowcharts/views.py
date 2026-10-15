from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.flowcharts.services import flowchart_payload
from apps.projects.services import get_algorithm


class FlowchartView(APIView):
    def get(self, request: Request, algorithm_id) -> Response:
        return Response(flowchart_payload(get_algorithm(request.user, algorithm_id)))
