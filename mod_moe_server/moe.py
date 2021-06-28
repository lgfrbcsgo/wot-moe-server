from collections import namedtuple
from typing import Dict

MoE = namedtuple("MoE", ("percentage", "damage", "marks", "battles"))


def moe_to_dict(moe):
    # type: (MoE) -> Dict
    return {
        "percentage": moe.percentage,
        "damage": moe.damage,
        "battles": moe.battles,
        "marks": moe.marks,
    }
