from collections import namedtuple

import dossiers2
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers import dependency
from skeletons.gui.shared import IItemsCache

items_cache = dependency.instance(IItemsCache)


MoE = namedtuple("MoE", ("percentage", "damage", "battles"))


def get_vehicle_dossier_descr(int_cd):
    dossier = items_cache.items.dossiers.getVehicleDossier(int_cd)
    return dossiers2.getVehicleDossierDescr(dossier)


def get_moe(int_cd):
    descr = get_vehicle_dossier_descr(int_cd)
    return MoE(
        percentage=descr["achievements"]["damageRating"] / 100.0,
        damage=descr["achievements"]["movingAvgDamage"],
        battles=descr["a15x15"]["battlesCount"],
    )


def get_all_moe():
    vehicles = items_cache.items.getVehicles(REQ_CRITERIA.INVENTORY)
    return {int_cd: get_moe(int_cd) for int_cd in vehicles.iterkeys()}
