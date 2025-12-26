"""BVG (Berliner Verkehrsbetriebe) profile for pyhafas.

Based on hafas-client JavaScript implementation:
https://github.com/public-transport/hafas-client/tree/main/p/bvg

Note: BVG and VBB profiles both work for Berlin stations.
The VBB profile is also available and may be preferred.
"""

import pytz
from pyhafas.profile.base import BaseProfile


class BVGProfile(BaseProfile):
    """
    Profile of the HaFAS of Berliner Verkehrsbetriebe (BVG).

    Based on the JavaScript hafas-client BVG profile configuration.
    Works for Berlin public transport stations.
    """

    baseUrl = "https://fahrinfo.vbb.de/bin/mgate.exe"  # noqa: N815
    defaultUserAgent = "VBB/3.0.0 (iPhone; iOS 13.1.2; Scale/2.00)"  # noqa: N815

    salt = "7x8i3q2m5N9wV4vR"
    addChecksum = True  # noqa: N815

    locale = "de-DE"
    timezone = pytz.timezone("Europe/Berlin")

    requestBody = {  # noqa: N815, RUF012
        "client": {"id": "VBB", "v": "3000000", "type": "IPH", "name": "VBB"},
        "ext": "VBB.R21.12.a",
        "ver": "1.15",
        "auth": {"type": "AID", "aid": "n91dB8Z77MLdoR0K"},
    }

    availableProducts = {  # noqa: N815, RUF012
        "suburban": [1],  # S-Bahn
        "subway": [2],  # U-Bahn
        "tram": [4],  # Tram
        "bus": [8],  # Bus
        "ferry": [16],  # Ferry
        "regional": [32],  # Regional
        "regional_express": [64],  # RE
        "long_distance": [128],  # IC/EC
        "long_distance_express": [256],  # ICE
    }

    defaultProducts = [  # noqa: N815, RUF012
        "suburban",
        "subway",
        "tram",
        "bus",
        "ferry",
        "regional",
        "regional_express",
    ]
