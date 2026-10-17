from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.flowcharts.services import flowchart_payload
from apps.projects.services import get_readable_algorithm


class FlowchartView(APIView):
    def get(self, request: Request, algorithm_id) -> Response:
        algorithm = get_readable_algorithm(request.user, algorithm_id)
        return Response(flowchart_payload(algorithm, persist=algorithm.owner_id == request.user.id))
