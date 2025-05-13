from enum import Enum

class Distribution(Enum):
    """Enum for thumbnail distribution models."""
    UNIFORM = 'uniform'
    TRIANGULAR = 'triangular'
    NORMAL = 'normal'