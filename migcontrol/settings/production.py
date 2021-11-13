from .base import *  # noqa

DEBUG = False

COMPRESS_ENABLED = True
COMPRESS_OFFLINE = True

try:
    from .local import *  # noqa
except ImportError:
    pass
