from .base import *  # noqa

DEBUG = False

COMPRESS_ENABLED = True

try:
    from .local import *  # noqa
except ImportError:
    pass
