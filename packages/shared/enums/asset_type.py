from enum import Enum


class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"
