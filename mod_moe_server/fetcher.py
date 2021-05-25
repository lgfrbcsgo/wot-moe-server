from collections import namedtuple

import dossiers2
from chat_shared import SYS_MESSAGE_TYPE
from constants import CURRENT_REALM
from Event import Event
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers import dependency
from messenger.proto.events import g_messengerEvents
from mod_moe_server.util import safe_callback
from PlayerEvents import g_playerEvents
from skeletons.connection_mgr import IConnectionManager
from skeletons.gui.shared import IItemsCache

items_cache = dependency.instance(IItemsCache)
connection_mgr = dependency.instance(IConnectionManager)


MoE = namedtuple("MoE", ("percentage", "damage", "battles"))


class MoeFetcher(object):
    def __init__(self):
        self.moe_fetched = Event()
        self.logged_in = Event()
        self._pending = []
        self._account_is_player = False
        self._first_sync = False

    def start(self):
        g_playerEvents.onAccountBecomePlayer += self._on_account_become_player
        g_playerEvents.onAccountBecomeNonPlayer += self._on_account_become_non_player
        g_messengerEvents.serviceChannel.onChatMessageReceived += self._on_sys_message
        items_cache.onSyncCompleted += self._on_cache_synced
        connection_mgr.onLoggedOn += self._on_logged_on

    def stop(self):
        g_playerEvents.onAccountBecomePlayer -= self._on_account_become_player
        g_playerEvents.onAccountBecomeNonPlayer -= self._on_account_become_non_player
        g_messengerEvents.serviceChannel.onChatMessageReceived -= self._on_sys_message
        items_cache.onSyncCompleted -= self._on_cache_synced
        connection_mgr.onLoggedOn -= self._on_logged_on

    @safe_callback
    def _on_account_become_player(self, *_, **__):
        self._account_is_player = True

    @safe_callback
    def _on_account_become_non_player(self, *_, **__):
        self._account_is_player = False

    @safe_callback
    def _on_sys_message(self, _, message, *__, **___):
        if message.type == SYS_MESSAGE_TYPE.battleResults.index():
            vehicles = message.data["playerVehicles"].iterkeys()
            self._pending.extend(vehicles)

    @safe_callback
    def _on_logged_on(self, data):
        self._first_sync = True
        self.logged_in(data["name"], CURRENT_REALM)

    @safe_callback
    def _on_cache_synced(self, *_, **__):
        if not self._account_is_player:
            return

        if self._first_sync:
            self._first_sync = False
            criteria = REQ_CRITERIA.INVENTORY | REQ_CRITERIA.VEHICLE.LEVELS(
                [5, 6, 7, 8, 9, 10]
            )
            self._pending.extend(items_cache.items.getVehicles(criteria).iterkeys())

        moe = self._get_all_moe(self._pending)
        self._pending = []
        self.moe_fetched(moe)

    @staticmethod
    def _get_vehicle_dossier_descr(int_cd):
        dossier = items_cache.items.dossiers.getVehicleDossier(int_cd)
        return dossiers2.getVehicleDossierDescr(dossier)

    @classmethod
    def _get_moe(cls, int_cd):
        descr = cls._get_vehicle_dossier_descr(int_cd)
        return MoE(
            percentage=descr["achievements"]["damageRating"] / 100.0,
            damage=descr["achievements"]["movingAvgDamage"],
            battles=descr["a15x15"]["battlesCount"],
        )

    @classmethod
    def _get_all_moe(cls, int_cds):
        return {int_cd: cls._get_moe(int_cd) for int_cd in int_cds}
