# Copyright (c) 2023 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

from __future__ import annotations

import logging

from abc import ABC, abstractmethod
from enum import IntEnum
from logging import Logger
from typing import Any, Callable, List, Optional, Tuple, Union
from typing import Protocol, runtime_checkable

# environs
from environs import Env

# grpcio
import grpc.aio
from grpc.aio import Server, ServerInterceptor

# opentelemetry-instrumentation-grpc
from opentelemetry.instrumentation.grpc import aio_server_interceptor

# opentelemetry-sdk
import opentelemetry.metrics
import opentelemetry.trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME as RESOURCE_SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider


class App:
    DEFAULT_NAME: str = "extend-app-service-extension"
    DEFAULT_PORT: int = 6565
    DEFAULT_LOG_LEVEL: Union[int, str] = logging.DEBUG

    def __init__(
        self,
        name: Optional[str] = None,
        port: Optional[int] = None,
        log_level: Optional[Union[int, str]] = None,
        env: Optional[Env] = None,
        logger: Optional[Logger] = None,
        options: Optional[List[AppOption]] = None,
    ) -> None:
        if env is None:
            env = Env()
            env.read_env()

        if not name:
            val = env.str("SERVICE_NAME", env.str("OTEL_SERVICE_NAME", None))
            name = f"extend-app-se-{val.strip().lower()}" if val else self.DEFAULT_NAME

        if port is None:
            port = env.int("SERVICE_PORT", self.DEFAULT_PORT)

        if log_level is None:
            log_level = env.log_level("SERVICE_LOG_LEVEL", self.DEFAULT_LOG_LEVEL)

        if logger is None:
            logger = logging.getLogger(name)
            logger.addHandler(logging.StreamHandler())
            logger.setLevel(log_level)

        if not options:
            options = []

        self.name: str = name
        self.port: int = port
        self.env: Env = env
        self.logger: Logger = logger
        self.options: List[AppOption] = list(
            sorted(options, key=lambda o: o.get_order())
        )

        self.grpc_interceptors: List[ServerInterceptor] = [aio_server_interceptor()]
        self.grpc_server: Optional[Server] = None
        self.grpc_service_names: List[str] = []
        self.otel_metric_readers: List[MetricReader] = []
        self.otel_resource: Resource = Resource({RESOURCE_SERVICE_NAME: self.name})

        self.is_initialized: bool = False

    def initialize(self, *args, **kwargs) -> None:
        if self.is_initialized:
            return

        self.apply_option_range(
            (
                AppOptionApplyOrderEnum.DEFAULT,
                AppOptionApplyOrderEnum.SET_OTEL_TRACER_PROVIDER,
            ),
            *args,
            **kwargs,
        )

        tracer_provider = TracerProvider(resource=self.otel_resource)
        opentelemetry.trace.set_tracer_provider(tracer_provider=tracer_provider)
        self.logger.info("opentelemetry tracer provider set")

        self.apply_option_range(
            (
                AppOptionApplyOrderEnum.SET_OTEL_TRACER_PROVIDER,
                AppOptionApplyOrderEnum.SET_OTEL_METER_PROVIDER,
            ),
            *args,
            **kwargs,
        )

        meter_provider = MeterProvider(
            metric_readers=self.otel_metric_readers, resource=self.otel_resource
        )
        opentelemetry.metrics.set_meter_provider(meter_provider=meter_provider)
        self.logger.info("opentelemetry meter provider set")

        self.apply_option_range(
            (
                AppOptionApplyOrderEnum.SET_OTEL_METER_PROVIDER,
                AppOptionApplyOrderEnum.CREATE_GRPC_SERVER,
            ),
            *args,
            **kwargs,
        )

        self.grpc_server = grpc.aio.server(interceptors=self.grpc_interceptors,options=[("grpc.max_metadata_size", 2**14)])
        self.logger.info("gRPC server created")

        self.apply_option_range(
            (
                AppOptionApplyOrderEnum.CREATE_GRPC_SERVER,
                AppOptionApplyOrderEnum.ADD_GRPC_SERVICES,
            ),
            *args,
            **kwargs,
        )
        self.logger.info("gRPC services added")

        self.apply_option_range(
            (
                AppOptionApplyOrderEnum.ADD_GRPC_SERVICES,
                AppOptionApplyOrderEnum.MAX + 1,
            ),
            *args,
            **kwargs,
        )

        self.is_initialized = True
        self.logger.info("initialization finished")

    async def run(self, termination_timeout: Optional[float] = None) -> None:
        if not self.is_initialized:
            self.initialize()

        assert self.grpc_server is not None

        self.grpc_server.add_insecure_port("[::]:{}".format(self.port))
        self.logger.info("gRPC server is starting")
        await self.grpc_server.start()

        await self.grpc_server.wait_for_termination(timeout=termination_timeout)
        self.logger.info("gRPC server has terminated")

    # noinspection PyShadowingBuiltins
    def apply_option_range(
        self, range: Union[int, Tuple[int, int]], /, *args, **kwargs
    ) -> None:
        min, max = range if isinstance(range, tuple) else (0, range)
        min, max = int(min), int(max)
        self.logger.debug("applying options [%s:%d)", min, max)
        for option in self.options:
            order = int(option.get_order())
            if min <= order < max:
                option.apply(self, *args, **kwargs)
                self.logger.info(
                    "applied option: %s (%d)",
                    self.get_option_name(option=option),
                    order,
                )

    @staticmethod
    def get_option_name(option: AppOption) -> str:
        if hasattr(option, "__name__"):
            return option.__name__
        if hasattr(option, "__class__"):
            return option.__class__.__name__
        return str(option)


class AppOptionApplyOrderEnum(IntEnum):
    DEFAULT = 0
    SET_OTEL_TRACER_PROVIDER = 64
    SET_OTEL_METER_PROVIDER = 128
    CREATE_GRPC_SERVER = 192
    ADD_GRPC_SERVICES = 256
    MAX = 512


@runtime_checkable
class AppOptionApplyFunc(Protocol):
    def __call__(self, app: App, /, *args, **kwargs) -> None:
        ...


@runtime_checkable
class AppOption(Protocol):
    def apply(self, app: App, /, *args, **kwargs) -> None:
        ...

    def get_order(self) -> Union[int, AppOptionApplyOrderEnum]:
        ...


class AppOptionBase(ABC):
    @abstractmethod
    def apply(self, app: App, /, *args, **kwargs) -> None:
        pass

    def get_name(self) -> str:
        return self.__class__.__name__

    # noinspection PyMethodMayBeStatic
    def get_order(self) -> Union[int, AppOptionApplyOrderEnum]:
        return 0

    def __repr__(self) -> str:
        return "{} ({})".format(self.get_name(), self.get_order())


assert issubclass(AppOptionBase, AppOption)


class AppOptionFunc(AppOptionBase):
    def __init__(
        self,
        name: str,
        /,
        order: Union[int, AppOptionApplyOrderEnum],
        apply_fn: AppOptionApplyFunc,
    ) -> None:
        self.__name = name
        self.__order = order
        self.__apply_fn = apply_fn

    def apply(self, app: App, /, *args, **kwargs) -> None:
        return self.__apply_fn(app, *args, **kwargs)

    def get_name(self) -> str:
        return self.__name

    def get_order(self) -> Union[int, AppOptionApplyOrderEnum]:
        return self.__order


class AppOptionGRPCInterceptor(AppOptionBase):
    def __init__(self, interceptor: ServerInterceptor) -> None:
        assert isinstance(interceptor, ServerInterceptor)
        self.interceptor = interceptor
        self.__name__ = "AppOptionGRPCInterceptor[{}]".format(
            self.interceptor.__class__.__name__
        )

    def apply(self, app: App, /, *args, **kwargs) -> None:
        app.grpc_interceptors.append(self.interceptor)

    def get_name(self) -> str:
        return self.__name__

    def get_order(self) -> Union[int, AppOptionApplyOrderEnum]:
        return AppOptionApplyOrderEnum.CREATE_GRPC_SERVER - 1


class AppOptionGRPCService(AppOptionBase):
    def __init__(
        self,
        full_name: str,
        service: Any,
        add_service_fn: Callable[[Any, Server], None],
    ) -> None:
        self.full_name = full_name
        self.service = service
        self.add_service_fn = add_service_fn
        self.__name__ = "AppOptionGRPCService[{}]".format(self.full_name)

    def apply(self, app: App, /, *args, **kwargs) -> None:
        self.add_service_fn(self.service, app.grpc_server)
        app.grpc_service_names.append(self.full_name)

    def get_name(self) -> str:
        return self.__name__

    def get_order(self) -> Union[int, AppOptionApplyOrderEnum]:
        return AppOptionApplyOrderEnum.ADD_GRPC_SERVICES - 1


__all__ = [
    "App",
    "AppOption",
    "AppOptionApplyFunc",
    "AppOptionApplyOrderEnum",
    "AppOptionBase",
    "AppOptionFunc",
    "AppOptionGRPCInterceptor",
    "AppOptionGRPCService",
]
