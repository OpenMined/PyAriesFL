"""Federated learning message admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema

from ...storage.error import StorageNotFoundError

from ..connections.manager import ConnectionManager
from ..connections.models.connection_record import ConnectionRecord

from .messages.federatedlearningmessage import FederatedLearningMessage


class SendMessageSchema(Schema):
    """Request schema for sending a message."""

    content = fields.Str(
        description="Message content",
        example="Hello"
    )


@docs(tags=["federatedlearningmessage"], summary="Send a federated learning message to a connection")
@request_schema(SendMessageSchema())
async def connections_send_federated_learning_message(request: web.BaseRequest):
    """
    Request handler for sending a federated learnng message to a connection.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.json()

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    if connection.is_ready:
        msg = FederatedLearningMessage(content=params["content"])
        await outbound_handler(msg, connection_id=connection_id)

        conn_mgr = ConnectionManager(context)
        await conn_mgr.log_activity(
            connection,
            "message",
            connection.DIRECTION_SENT,
            {"content": params["content"]},
        )

    return web.json_response({})


@docs(tags=["federatedlearningmessage"], summary="Expire a copyable federatedlearningmessage")
async def connections_expire_federated_learning_message(request: web.BaseRequest):
    """
    Request handler for sending a federated learning message to a connection.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    activity_id = request.match_info["activity_id"]
    activity = await connection.retrieve_activity(context, activity_id)
    meta = activity.get("meta") or {}
    if meta.get("copy_invite"):
        meta["copied"] = 1
        await connection.update_activity_meta(context, activity_id, meta)

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [web.post("/connections/{id}/send-fl-message", connections_send_federated_learning_message)]
    )

    app.add_routes(
        [
            web.post(
                "/connections/{id}/expire-fl-message/{activity_id}",
                connections_expire_federated_learning_message,
            )
        ]
    )
