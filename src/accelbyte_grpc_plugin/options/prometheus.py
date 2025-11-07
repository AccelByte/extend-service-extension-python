# Copyright (c) 2023 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

import threading
from typing import Optional, Union

from flask import Flask
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from ..app import App, AppOptionApplyOrderEnum, AppOptionBase


class AppOptionPrometheus(AppOptionBase):
    DEFAULT_ADDR: str = "0.0.0.0"
    DEFAULT_PORT: int = 8080
    DEFAULT_ENDPOINT: str = "/metrics"

    def __init__(
        self,
        addr: Optional[str] = None,
        port: Optional[int] = None,
        endpoint: Optional[str] = None,
    ) -> None:
        self.addr = addr
        self.port = port
        self.endpoint = endpoint

    def apply(self, app: App, /, *args, **kwargs) -> None:
        with app.env.prefixed("PROMETHEUS_"):
            if not self.addr:
                self.addr = app.env.str("ADDR", self.DEFAULT_ADDR)
            if self.port is None:
                self.port = app.env.int("PORT", self.DEFAULT_PORT)
            if not self.endpoint:
                self.endpoint = app.env.str("ENDPOINT", self.DEFAULT_ENDPOINT)
            prefix = app.env.str("PREFIX", app.name)
            mounts = {self.endpoint: make_wsgi_app()}
            flask_app = Flask(import_name=app.name)
            flask_app.wsgi_app = DispatcherMiddleware(
                app=flask_app.wsgi_app, mounts=mounts
            )
            threading.Thread(
                target=lambda: flask_app.run(
                    host=self.addr,
                    port=self.port,
                    debug=True,
                    use_reloader=False,
                )
            ).start()
            app.otel_metric_readers.append(PrometheusMetricReader(prefix))

    def get_order(self) -> Union[int, AppOptionApplyOrderEnum]:
        return AppOptionApplyOrderEnum.SET_OTEL_METER_PROVIDER - 1


__all__ = [
    "AppOptionPrometheus",
]
