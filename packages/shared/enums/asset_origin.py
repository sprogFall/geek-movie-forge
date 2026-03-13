from enum import Enum


class AssetOrigin(str, Enum):
    MANUAL = "manual"
    GENERATED = "generated"
