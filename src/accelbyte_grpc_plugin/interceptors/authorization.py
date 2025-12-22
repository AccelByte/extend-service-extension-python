# Copyright (c) 2023 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

from typing import Awaitable, Callable, Optional, Tuple

import grpc
from grpc import HandlerCallDetails, RpcMethodHandler, StatusCode
from grpc.aio import ServerInterceptor

from google.protobuf.descriptor import MethodDescriptor
from google.protobuf.descriptor_pool import Default as DescriptorPool

from accelbyte_grpc_plugin.utils import (
    get_headers_from_metadata,
    get_propagator_header_keys,
)

from accelbyte_py_sdk.services.auth import parse_access_token
from accelbyte_py_sdk.token_validation import TokenValidatorProtocol
from accelbyte_py_sdk.token_validation._ctypes import (
    InsufficientPermissionsError,
    TokenRevokedError,
    UserRevokedError,
)


class AuthorizationServerInterceptor(ServerInterceptor):
    def __init__(
        self,
        token_validator: TokenValidatorProtocol,
        namespace: Optional[str] = None,
    ) -> None:
        self.token_validator = token_validator
        self.namespace = namespace

    async def intercept_service(
        self,
        continuation: Callable[[HandlerCallDetails], Awaitable[RpcMethodHandler]],
        handler_call_details: HandlerCallDetails,
    ) -> RpcMethodHandler:
        method = getattr(handler_call_details, "method", "")
        method_descriptor = self.get_method_descriptor(method=method)

        if not method_descriptor:
            return self.create_aio_rpc_error(
                error="method not found", code=StatusCode.INTERNAL
            )

        # Check if method requires Bearer authentication from OpenAPI annotations
        require_token = self.has_bearer_security(method_descriptor)

        # Extract permission extensions
        resource, action = self.extract_permissions(method_descriptor)

        # Skip auth if no security requirements
        if not require_token and resource is None and action is None:
            return await continuation(handler_call_details)

        # At this point, either Bearer security or permissions are required
        headers = get_headers_from_metadata(handler_call_details=handler_call_details)

        authorization = headers.get("authorization", None)

        if not authorization:
            return self.create_aio_rpc_error(error="no authorization token found")

        if not authorization.startswith("Bearer "):
            return self.create_aio_rpc_error(error="invalid authorization token format")

        try:
            # by default, any HTTP calls inside an interceptor does not propagate headers
            propagator_header_keys = get_propagator_header_keys()
            propagator_headers = {
                k: v for k, v in headers.items() if k in propagator_header_keys
            }

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

    @staticmethod
    def extract_permissions(
        method_descriptor: MethodDescriptor,
    ) -> Tuple[Optional[str], Optional[int]]:
        """Extract resource and action from permission extensions"""
        resource: Optional[str] = None
        action: Optional[int] = None

        permission_resource_descriptor = (
            AuthorizationServerInterceptor.get_option_descriptor("permission.resource")
        )
        permission_action_descriptor = (
            AuthorizationServerInterceptor.get_option_descriptor("permission.action")
        )

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

        return resource, action

    @staticmethod
    def has_bearer_security(method_descriptor: MethodDescriptor) -> bool:
        """Check if method requires Bearer token from OpenAPI v2 security annotation"""
        try:
            openapiv2_operation_descriptor = (
                AuthorizationServerInterceptor.get_option_descriptor(
                    "grpc.gateway.protoc_gen_openapiv2.options.openapiv2_operation"
                )
            )
            if not openapiv2_operation_descriptor:
                return False

            method_options = method_descriptor.GetOptions()
            operation = method_options.Extensions[openapiv2_operation_descriptor]

            if operation and hasattr(operation, "security"):
                for security_obj in operation.security:
                    if hasattr(security_obj, "security_requirement"):
                        if "Bearer" in security_obj.security_requirement:
                            return True
            return False
        except (KeyError, AttributeError):
            return False


__all__ = [
    "AuthorizationServerInterceptor",
]
