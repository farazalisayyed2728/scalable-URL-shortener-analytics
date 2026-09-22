from .base import *  # noqa: F403

# Enforce DEBUG mode for development overrides
DEBUG = True

# Add DRF browsable API only in local development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]