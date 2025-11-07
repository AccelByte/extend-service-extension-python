# Copyright (c) 2023 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

from typing import Union

import opentelemetry.trace
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from ..app import App, AppOptionApplyOrderEnum, AppOptionBase


class AppOptionZipkin(AppOptionBase):
    DEFAULT_ENDPOINT: str = "http://localhost:9411/api/v2/spans"

    def apply(self, app: App, /, *args, **kwargs) -> None:
        with app.env.prefixed("OTEL_EXPORTER_ZIPKIN_"):
            endpoint = app.env.str("ENDPOINT", self.DEFAULT_ENDPOINT)
            span_exporter = ZipkinExporter(endpoint=endpoint)
            span_processor = BatchSpanProcessor(span_exporter=span_exporter)
            tracer_provider = opentelemetry.trace.get_tracer_provider()
            tracer_provider.add_span_processor(span_processor=span_processor)

    def get_order(self) -> Union[int, AppOptionApplyOrderEnum]:
        return AppOptionApplyOrderEnum.SET_OTEL_TRACER_PROVIDER + 1


__all__ = [
    "AppOptionZipkin",
]
