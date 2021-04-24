import re

from debug_utils import LOG_NOTE
from mod_async import CallbackCancelled, async_task, auto_run, delay
from mod_async_server import Server
from mod_websocket_server import websocket_protocol, MessageStream

PORT = 15456

ORIGIN_WHITELIST = [
    re.compile("^https?://localhost(:[0-9]{1,5})?$"),
    "https://lgfrbcsgo.github.io",
]


@websocket_protocol(allowed_origins=ORIGIN_WHITELIST)
@async_task
def protocol(server, stream):
    # type: (Server, MessageStream) -> ...
    host, port = stream.peer_addr
    origin = stream.handshake_headers["origin"]

    LOG_NOTE(
        "{origin} ([{host}]:{port}) connected.".format(
            origin=origin, host=host, port=port
        )
    )

    try:
        while True:
            data = yield stream.receive_message()
            yield stream.send_message(data)
    finally:
        LOG_NOTE(
            "{origin} ([{host}]:{port}) disconnected.".format(
                origin=origin, host=host, port=port
            )
        )


class MoeServer(object):
    def __init__(self):
        self._keep_running = True

    @auto_run
    @async_task
    def serve(self):
        LOG_NOTE("Starting server on port {}".format(PORT))

        try:
            with Server(protocol, PORT) as server:
                while self._keep_running and not server.closed:
                    server.poll()
                    yield delay(0)
        except CallbackCancelled:
            pass
        finally:
            LOG_NOTE("Stopped server")

    def close(self):
        self._keep_running = False


g_moe_server = MoeServer()
