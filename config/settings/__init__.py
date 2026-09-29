# In config/__init__.py:
import os
from celery import Celery

from celery import app as celery_app

__all__ = ("celery_app",)