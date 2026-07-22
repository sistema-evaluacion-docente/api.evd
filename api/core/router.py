"""Custom API router with response envelope support."""

from typing import Any, Callable, Coroutine

from fastapi import APIRouter
from fastapi.routing import APIRoute, get_request_handler
from starlette.requests import Request
from starlette.responses import Response

from api.schemas.response import ResponseEnvelope


class EnvelopeAPIRoute(APIRoute):
    """Custom APIRoute that skips response validation but keeps response_model for docs."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        return get_request_handler(
            dependant=self.dependant,
            body_field=self.body_field,
            status_code=self.status_code,
            response_class=self.response_class,
            response_field=None,
            response_model_include=self.response_model_include,
            response_model_exclude=self.response_model_exclude,
            response_model_by_alias=self.response_model_by_alias,
            response_model_exclude_unset=self.response_model_exclude_unset,
            response_model_exclude_defaults=self.response_model_exclude_defaults,
            response_model_exclude_none=self.response_model_exclude_none,
            dependency_overrides_provider=self.dependency_overrides_provider,
            embed_body_fields=self._embed_body_fields,
            strict_content_type=self.strict_content_type,
            stream_item_field=self.stream_item_field,
            is_json_stream=self.is_json_stream,
        )


class EnvelopeRouter(APIRouter):
    """Custom API router that automatically wraps responses in a response envelope."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("route_class", EnvelopeAPIRoute)
        super().__init__(*args, **kwargs)

    def add_api_route(
        self, path, endpoint, *, response_model=None, envelope: bool = True, **kwargs
    ):
        """Add an API route with optional response envelope support."""

        if envelope and response_model is not None:
            try:
                response_model = ResponseEnvelope[response_model]
            except TypeError:
                pass

        super().add_api_route(path, endpoint, response_model=response_model, **kwargs)
