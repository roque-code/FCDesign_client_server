from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.editor.services import preference_payload, update_preference
from apps.http import current_user, object_body


class PreferenceView(APIView):
    def get(self, request: Request) -> Response:
        return Response(preference_payload(current_user(request).editor_preference))

    def patch(self, request: Request) -> Response:
        preference = update_preference(
            current_user(request).editor_preference,
            object_body(request.data),
        )
        return Response(preference_payload(preference))
