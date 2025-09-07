# Copyright (c) 2023 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

from typing import Awaitable, Callable, List, Optional

import grpc
from grpc import HandlerCallDetails, RpcMethodHandler, StatusCode
from grpc.aio import ServerInterceptor

from google.protobuf.descriptor import MethodDescriptor
from google.protobuf.descriptor_pool import Default as DescriptorPool

from accelbyte_grpc_plugin.utils import get_headers_from_metadata, get_propagator_header_keys

from accelbyte_py_sdk.services.auth import parse_access_token
from accelbyte_py_sdk.token_validation import TokenValidatorProtocol
from accelbyte_py_sdk.token_validation._ctypes import (
    InsufficientPermissionsError,
    TokenRevokedError,
    UserRevokedError,
)


class AuthorizationServerInterceptor(ServerInterceptor):
    whitelisted_methods: List[str] = [
        "/grpc.health.v1.Health/Check",
        "/grpc.health.v1.Health/Watch",
        "/grpc.reflection.v1alpha.ServerReflection/ServerReflectionInfo",
    ]

    def __init__(
        self,
        token_validator: TokenValidatorProtocol,
        resource: Optional[str] = None,
        action: Optional[int] = None,
        namespace: Optional[str] = None,
    ) -> None:
        self.token_validator = token_validator
        self.resource = resource
        self.action = action
        self.namespace = namespace

    async def intercept_service(
        self,
        continuation: Callable[[HandlerCallDetails], Awaitable[RpcMethodHandler]],
        handler_call_details: HandlerCallDetails,
    ) -> RpcMethodHandler:
        method = getattr(handler_call_details, "method", "")
        if method in self.whitelisted_methods:
            return await continuation(handler_call_details)

        method_descriptor = self.get_method_descriptor(method=method)
        if not method_descriptor:
            return self.create_aio_rpc_error(error="method not found", code=StatusCode.INTERNAL)

        resource: Optional[str] = None
        action: Optional[int] = None

        permission_resource_descriptor = self.get_option_descriptor("permission.resource")
        permission_action_descriptor = self.get_option_descriptor("permission.action")

        if permission_resource_descriptor and permission_action_descriptor:
            method_options = method_descriptor.GetOptions()

            try:
                resource = method_options.Extensions[permission_resource_descriptor]
                if not resource:
                    resource = None
            except KeyError:
                pass

            try:
                action = method_options.Extensions[permission_action_descriptor]
                if action == 0:
                    action = None
            except KeyError:
                pass

        if resource is None:
            resource = self.resource

        if action is None:
            action = self.action

        headers = get_headers_from_metadata(handler_call_details=handler_call_details)

        authorization = headers.get("authorization", None)

        if not authorization:
            return self.create_aio_rpc_error(error="no authorization token found")

        if not authorization.startswith("Bearer "):
            return self.create_aio_rpc_error(error="invalid authorization token format")

        try:
            # by default, any HTTP calls inside an interceptor does not propagate headers
            propagator_header_keys = get_propagator_header_keys()
            propagator_headers = {k: v for k, v in headers.items() if k in propagator_header_keys}

            token = authorization.removeprefix("Bearer ")
            error = self.token_validator.validate_token(
                token=token,
                resource=resource,
                action=action,
                namespace=self.namespace,
                x_additional_headers=propagator_headers,
            )
            if error is not None:
                if isinstance(error, InsufficientPermissionsError):
                    return self.create_aio_rpc_error(
                        error=f"insufficient permissions: resource: {resource}, action: {action}",
                        code=StatusCode.PERMISSION_DENIED,
                    )
                elif isinstance(error, (TokenRevokedError, UserRevokedError)):
                    return self.create_aio_rpc_error(
                        error=f"authorization token was already revoked",
                        code=StatusCode.PERMISSION_DENIED,
                    )
                else:
                    return self.create_aio_rpc_error(
                        error=f"ValidateToken.{type(error).__name__}: {error}",
                        code=StatusCode.UNAUTHENTICATED,
                    )
        except Exception as error:
            return self.create_aio_rpc_error(
                error=f"ValidateToken.{type(error).__name__}: {error}",
                code=StatusCode.INTERNAL,
            )

        try:
            claims, error = parse_access_token(token)
            if error is not None:
                return self.create_aio_rpc_error(
                    error=f"ParceAccessToken.{type(error).__name__}: {error}",
                    code=StatusCode.UNAUTHENTICATED,
                )
            if extend_namespace := claims.get("extend_namespace", None):
                if extend_namespace != self.namespace:
                    return self.create_aio_rpc_error(
                        error=f"'{extend_namespace}' does not match '{self.namespace}'",
                        code=StatusCode.PERMISSION_DENIED,
                    )
        except Exception as error:
            return self.create_aio_rpc_error(
                error=f"ParceAccessToken.{type(error).__name__}: {error}",
                code=StatusCode.INTERNAL,
            )

        return await continuation(handler_call_details)

    @staticmethod
    def create_aio_rpc_error(error: str, code: StatusCode = StatusCode.UNAUTHENTICATED):
        async def abort(ignored_request, context):
            await context.abort(code, error)

        return grpc.unary_unary_rpc_method_handler(abort)

    @staticmethod
    def get_method_descriptor(method: str) -> Optional[MethodDescriptor]:
        parts = method.removeprefix("/").split("/")
        if len(parts) != 2:
            return None
        try:
            service_name = parts[0]
            method_name = parts[1]
            service_descriptor = DescriptorPool().FindServiceByName(service_name)
            method_descriptor = service_descriptor.methods_by_name[method_name]
            return method_descriptor
        except KeyError:
            return None

    @staticmethod
    def get_option_descriptor(option: str):
        try:
            option_descriptor = DescriptorPool().FindExtensionByName(option)
            return option_descriptor
        except KeyError:
            return None


__all__ = [
    "AuthorizationServerInterceptor",
]
