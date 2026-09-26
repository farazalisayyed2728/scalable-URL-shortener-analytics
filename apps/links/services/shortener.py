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
    """
    Domain service responsible for creating a ShortURL record.
    Guarantees concurrency-safe allocation using DB-level constraints and savepoints.
    """
    # 1. Validate destination URL
    validated_url = validate_original_url(original_url)

    # 2. Case A: User supplied a custom short code
    if custom_code:
        valid_custom_code = validate_custom_code(custom_code)
        try:
            with transaction.atomic():
                return ShortURL.objects.create(
                    short_code=valid_custom_code,
                    original_url=validated_url,
                    owner=owner,
                    is_custom=True,
                    expires_at=expires_at,
                )
# Inside create_short_url, right before returning the instance in Case A (Custom Code):
        except IntegrityError:
            raise CodeAlreadyTakenException()
        else:
            # Clear any negative cache entry created if someone previously hit this code
            delete_cached_url(valid_custom_code)
            return link_instance

    # 3. Case B: Random short-code generation with collision retry loop
    max_retries = settings.MAX_CODE_RETRIES
    code_length = settings.CODE_LENGTH

    for attempt in range(max_retries):
        generated_code = generate_random_code(length=code_length)
        try:
            # We wrap the attempt in an atomic block (Savepoint).
            # If an IntegrityError occurs, PostgreSQL aborts ONLY this savepoint,
            # allowing the loop to safely retry without spoiling an outer transaction.
            with transaction.atomic():
                return ShortURL.objects.create(
                    short_code=generated_code,
                    original_url=validated_url,
                    owner=owner,
                    is_custom=False,
                    expires_at=expires_at,
                )
# And similarly in Case B (Random Code), right after successful creation:
        except IntegrityError:
            continue
        else:
            delete_cached_url(generated_code)
            return link_instance
        
    # 4. If all retry attempts collided, raise 503
    raise CodeGenerationFailedException()