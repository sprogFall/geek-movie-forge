from enum import Enum


class ModelCapability(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
