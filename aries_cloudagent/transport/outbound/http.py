"""Http outbound transport."""

import logging

from aiohttp import ClientSession

from ...messaging.outbound_message import OutboundMessage

from .base import BaseOutboundTransport


class HttpTransport(BaseOutboundTransport):
    """Http outbound transport class."""

    schemes = ("http", "https")

    def __init__(self) -> None:
        """Initialize an `HttpTransport` instance."""
        super(HttpTransport, self).__init__()
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start the transport."""
        self.client_session = ClientSession()
        return self

    async def stop(self):
        """Stop the transport."""
        await self.client_session.close()
        self.client_session = None

    async def handle_message(self, message: OutboundMessage):
        """
        Handle message from queue.

        Args:
            message: `OutboundMessage` to send over transport implementation
        """
        headers = {}
        if isinstance(message.payload, bytes):
            headers["Content-Type"] = "application/ssi-agent-wire"
        else:
            headers["Content-Type"] = "application/json"
        async with self.client_session.post(
            message.endpoint, data=message.payload, headers=headers
        ) as response:
            if response.status < 200 or response.status > 299:
                raise Exception("Unexpected response status")
