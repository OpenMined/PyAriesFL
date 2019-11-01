"""FederatedLearning message handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ...connections.manager import ConnectionManager

from ..messages.federatedlearningmessage import FederatedLearningMessage


class FederatedLearningMessageHandler(BaseHandler):
    """Message handler class for federated learning messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for federated learning messages.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"FederatedLearningMessageHandler called with context {context}")
        assert isinstance(context.message, FederatedLearningMessage)

        self._logger.info("Received federated learnning message: %s", context.message.content)

        body = context.message.content
        meta = {"content": body}

        # For Workshop: mark invitations as copyable
        if context.message.content and context.message.content.startswith("http"):
            meta["copy_invite"] = True

        conn_mgr = ConnectionManager(context)
        await conn_mgr.log_activity(
            context.connection_record,
            "message",
            context.connection_record.DIRECTION_RECEIVED,
            meta,
        )

        await responder.send_webhook(
            "federeatedlearningmessages",
            {
                "connection_id": context.connection_record.connection_id,
                "message_id": context.message._id,
                "content": body,
                "state": "received"
            },
        )

        reply = None
        if context.settings.get("debug.auto_respond_messages"):
            if (
                "received your message" not in body
                and "received your invitation" not in body
            ):
                if context.message.content.startswith("http"):
                    reply = f"{context.default_label} received your invitation"
                else:
                    reply = f"{context.default_label} received your message"
        elif body.startswith("Reply with: "):
            reply = body[12:]

        if reply:
            reply_msg = FederatedLearningMessage(content=reply)
            if "l10n" in context.message._decorators:
                reply_msg._decorators["l10n"] = context.message._decorators["l10n"]
            await responder.send_reply(reply_msg)
            await conn_mgr.log_activity(
                context.connection_record,
                "message",
                context.connection_record.DIRECTION_SENT,
                {"content": reply},
            )
