import json
import re
from collections import defaultdict, namedtuple
from typing import Dict, List, Optional

from debug_utils import LOG_NOTE
from mod_async import CallbackCancelled, async_task, auto_run, delay
from mod_async_server import Server
from mod_moe_server.fetcher import MoE, MoeFetcher
from mod_websocket_server import MessageStream, websocket_protocol

PORT = 15456

ORIGIN_WHITELIST = [
    re.compile("^https?://localhost(:[0-9]{1,5})?$"),
    "https://lgfrbcsgo.github.io",
    "https://www.websocket.org",
]


@auto_run
@async_task
def send(stream, message):
    yield stream.send_message(json.dumps(message))


def moe_to_dict(moe):
    # type: (MoE) -> Dict
    return {"percentage": moe.percentage, "damage": moe.damage, "battles": moe.battles}


Account = namedtuple("Account", ("username", "realm"))


def account_to_str(account):
    # type: (Account) -> str
    return "{}_{}".format(account.username, account.realm)


class Handlers(object):
    def __init__(self):
        self._fetcher = MoeFetcher()
        self._connections = []  # type: List[MessageStream]
        self._current_account = None  # type: Optional[Account]
        self._session = defaultdict(lambda: defaultdict(lambda: []))

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
            self._send_session_message(stream)

    def handle_disconnect(self, stream):
        # type: (MessageStream) -> None
        if stream in self._connections:
            self._connections.remove(stream)

    def _on_logged_in(self, username, realm):
        # type: (str, str) -> None
        self._current_account = Account(username, realm)

    def _on_moe_update(self, vehicles):
        # type: (Dict[int, MoE]) -> None
        for int_cd, moe in vehicles.iteritems():
            self._session[self._current_account][int_cd].append(moe)

        self._send_moe_update_message(vehicles)

    def _send_session_message(self, stream):
        # type: (MessageStream) -> None
        message = {
            "type": "SESSION",
            "accounts": {
                account_to_str(account): {
                    int_cd: [moe_to_dict(moe) for moe in moe_values]
                    for int_cd, moe_values in vehicles.iteritems()
                }
                for account, vehicles in self._session.iteritems()
            },
        }
        send(stream, message)

    def _send_moe_update_message(self, vehicles):
        # type: (Dict[int, MoE]) -> None
        message = {
            "type": "MOE_UPDATE",
            "account": account_to_str(self._current_account),
            "vehicles": {
                int_cd: moe_to_dict(moe) for int_cd, moe in vehicles.iteritems()
            },
        }
        for stream in self._connections:
            send(stream, message)


def create_protocol(handlers):
    # type: (Handlers) -> ...

    @websocket_protocol(allowed_origins=ORIGIN_WHITELIST)
    @async_task
    def protocol(server, stream):
        # type: (Server, MessageStream) -> ...
        host, port = stream.peer_addr
        origin = stream.handshake_headers["origin"]

        handlers.accept_connection(stream)
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
            handlers.handle_disconnect(stream)
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

        handlers = Handlers()
        handlers.start()
        protocol = create_protocol(handlers)
        try:
            with Server(protocol, PORT) as server:
                while self._keep_running and not server.closed:
                    server.poll()
                    yield delay(0)
        except CallbackCancelled:
            pass
        finally:
            handlers.stop()
            LOG_NOTE("Stopped server")

    def close(self):
        self._keep_running = False


g_moe_server = MoeServer()
