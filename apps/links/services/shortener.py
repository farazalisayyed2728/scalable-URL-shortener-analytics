from datetime import datetime
from typing import Optional
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from .cache import delete_cached_url

from apps.core.exceptions import (
    CodeAlreadyTakenException,
    CodeGenerationFailedException,
)
from apps.links.models import ShortURL
from .generator import generate_random_code
from .validators import validate_custom_code, validate_original_url

User = get_user_model()


def create_short_url(
    *,
    original_url: str,
    owner: Optional[User] = None,
    custom_code: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> ShortURL:

    # 1. Validate destination URL
    validated_url = validate_original_url(original_url)

    # ---------------------------------------------------------
    # Case A: Custom short code
    # ---------------------------------------------------------
    if custom_code:
        valid_custom_code = validate_custom_code(custom_code)

        try:
            with transaction.atomic():
                link = ShortURL.objects.create(
                    short_code=valid_custom_code,
                    original_url=validated_url,
                    owner=owner,
                    is_custom=True,
                    expires_at=expires_at,
                )

        except IntegrityError:
            raise CodeAlreadyTakenException()

        # Cache invalidation happens AFTER successful DB creation
        delete_cached_url(valid_custom_code)

        return link

    # ---------------------------------------------------------
    # Case B: Random short-code generation
    # ---------------------------------------------------------
    max_retries = settings.MAX_CODE_RETRIES
    code_length = settings.CODE_LENGTH

    for _ in range(max_retries):

        generated_code = generate_random_code(
            length=code_length
        )

        try:
            with transaction.atomic():
                link = ShortURL.objects.create(
                    short_code=generated_code,
                    original_url=validated_url,
                    owner=owner,
                    is_custom=False,
                    expires_at=expires_at,
                )

        except IntegrityError:
            # Collision → try another random code
            continue

        # Successful creation
        delete_cached_url(generated_code)

        return link

    # All attempts collided
    raise CodeGenerationFailedException()