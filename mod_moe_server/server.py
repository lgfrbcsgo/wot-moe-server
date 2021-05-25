import json
import re
from typing import List

from debug_utils import LOG_NOTE
from mod_async import CallbackCancelled, async_task, auto_run, delay
from mod_async_server import Server
from mod_moe_server.fetcher import MoeFetcher
from mod_websocket_server import MessageStream, websocket_protocol

PORT = 15456

ORIGIN_WHITELIST = [
    re.compile("^https?://localhost(:[0-9]{1,5})?$"),
    "https://lgfrbcsgo.github.io",
    "https://www.websocket.org",
]


class MoeServerState(object):
    def __init__(self):
        self._fetcher = MoeFetcher()
        self._connections = []  # type: List[MessageStream]

    def start(self):
        self._fetcher.start()
        self._fetcher.moe_fetched += self._on_moe_update
        self._fetcher.logged_in += self._on_logged_in

    def stop(self):
        self._fetcher.stop()
        self._fetcher.moe_fetched -= self._on_moe_update
        self._fetcher.logged_in -= self._on_logged_in

    def accept_connection(self, stream):
        # type: (MessageStream) -> None
        if stream not in self._connections:
            self._connections.append(stream)

    def handle_disconnect(self, stream):
        # type: (MessageStream) -> None
        if stream in self._connections:
            self._connections.remove(stream)

    @auto_run
    @async_task
    def _on_logged_in(self, name, realm):
        for stream in self._connections:
            yield stream.send_message(json.dumps(dict(name=name, realm=realm)))

    @auto_run
    @async_task
    def _on_moe_update(self, data):
        for stream in self._connections:
            yield stream.send_message(json.dumps(data))


def create_protocol(state):
    # type: (MoeServerState) -> ...

    @websocket_protocol(allowed_origins=ORIGIN_WHITELIST)
    @async_task
    def protocol(server, stream):
        # type: (Server, MessageStream) -> ...
        host, port = stream.peer_addr
        origin = stream.handshake_headers["origin"]

        state.accept_connection(stream)
        LOG_NOTE(
            "{origin} ([{host}]:{port}) connected.".format(
                origin=origin, host=host, port=port
            )
        )

        try:
            while True:
                # ignore all messages
                yield stream.receive_message()
        finally:
            state.handle_disconnect(stream)
            LOG_NOTE(
                "{origin} ([{host}]:{port}) disconnected.".format(
                    origin=origin, host=host, port=port
                )
            )

    return protocol


class MoeServer(object):
    def __init__(self):
        self._keep_running = True

    @auto_run
    @async_task
    def serve(self):
        LOG_NOTE("Starting server on port {}".format(PORT))

        state = MoeServerState()
        state.start()
        protocol = create_protocol(state)
        try:
            with Server(protocol, PORT) as server:
                while self._keep_running and not server.closed:
                    server.poll()
                    yield delay(0)
        except CallbackCancelled:
            pass
        finally:
            state.stop()
            LOG_NOTE("Stopped server")

    def close(self):
        self._keep_running = False


g_moe_server = MoeServer()
