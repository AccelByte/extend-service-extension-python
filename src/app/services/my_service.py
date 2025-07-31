# Copyright (c) 2023 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

import uuid

from logging import Logger
from typing import Any

from google.protobuf.json_format import MessageToJson
from grpc import StatusCode

from accelbyte_py_sdk import AccelByteSDK
from accelbyte_py_sdk.api import cloudsave as cs_service
from accelbyte_py_sdk.api.cloudsave import models as cs_models

from accelbyte_grpc_plugin.utils import create_aio_rpc_error

from service_pb2 import (
    CreateOrUpdateGuildProgressRequest,
    CreateOrUpdateGuildProgressResponse,
    GetGuildProgressRequest,
    GetGuildProgressResponse,
    DESCRIPTOR,
)

from service_pb2_grpc import ServiceServicer


class AsyncService(ServiceServicer):
    full_name: str = DESCRIPTOR.services_by_name["Service"].full_name

    def __init__(self, sdk: AccelByteSDK, logger: Logger) -> None:
        self.sdk = sdk
        self.logger = logger

    # noinspection PyShadowingBuiltins
    def log_payload(self, format: str, payload: Any) -> None:
        if not self.logger:
            return
        payload_json = MessageToJson(payload, preserving_proto_field_name=True)
        self.logger.info(format.format(payload_json))

    @staticmethod
    def generate_new_guild_id() -> str:
        return str(uuid.uuid4()).replace("-", "")

    @staticmethod
    def format_guild_progress_key(guild_id: str) -> str:
        return f"guildProgress_{guild_id}"

    async def CreateOrUpdateGuildProgress(
        self, request: CreateOrUpdateGuildProgressRequest, context: Any
    ) -> CreateOrUpdateGuildProgressResponse:
        if not request.namespace:
            raise create_aio_rpc_error("", StatusCode.INVALID_ARGUMENT)

        guild_id = request.guild_progress.guild_id.strip()
        if not guild_id:
            guild_id = self.generate_new_guild_id()

        gp_key = self.format_guild_progress_key(guild_id)
        gp_value = cs_models.ModelsGameRecordRequest()
        gp_value["guild_id"] = guild_id
        gp_value["namespace"] = request.guild_progress.namespace
        gp_value["objectives"] = dict(request.guild_progress.objectives)

        (
            response,
            error,
        ) = await cs_service.admin_post_game_record_handler_v1_async(
            body=gp_value,
            key=gp_key,
            namespace=request.namespace,
            sdk=self.sdk,
        )
        if error:
            raise Exception(error)

        result = CreateOrUpdateGuildProgressResponse()
        result.guild_progress.guild_id = response.value["guild_id"]
        result.guild_progress.namespace = response.value["namespace"]
        for k, v in response.value["objectives"].items():
            result.guild_progress.objectives[k] = v

        return result

    async def GetGuildProgress(
        self, request: GetGuildProgressRequest, context: Any
    ) -> GetGuildProgressResponse:
        if not request.namespace:
            raise create_aio_rpc_error("", StatusCode.INVALID_ARGUMENT)

        gp_key = self.format_guild_progress_key(request.guild_id.strip())

        (
            response,
            error,
        ) = await cs_service.admin_get_game_record_handler_v1_async(
            key=gp_key,
            namespace=request.namespace,
            sdk=self.sdk,
        )
        if error:
            raise Exception(error)

        result = GetGuildProgressResponse()
        result.guild_progress.guild_id = response.value["guild_id"]
        result.guild_progress.namespace = response.value["namespace"]
        for k, v in response.value["objectives"].items():
            result.guild_progress.objectives[k] = v

        return result
