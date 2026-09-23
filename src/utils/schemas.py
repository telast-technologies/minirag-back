from typing import Annotated, Union

import phonenumbers
from fastapi import UploadFile
from pydantic import AfterValidator
from pydantic_extra_types.phone_numbers import PhoneNumberValidator

from src.config.exceptions import BadRequestException
from src.config.settings import settings

GenerationModel = Annotated[
    str,
    AfterValidator(
        lambda v: (
            v
            if v in settings.GENERATION_MODEL_IDS
            else (_ for _ in ()).throw(BadRequestException(f"Must be one of {settings.GENERATION_MODEL_IDS}"))
        )
    ),
]

FileWithValidation = Annotated[
    UploadFile,
    AfterValidator(
        lambda f: (
            (_ for _ in ()).throw(BadRequestException(f"File size exceeds limit: {settings.DOCUMENT_MAX_SIZE} MB"))
            if (f.size and f.size > settings.DOCUMENT_MAX_SIZE * 1024 * 1024)
            else (_ for _ in ()).throw(BadRequestException(f"Invalid file type: {f.content_type}"))
            if f.content_type not in settings.ALLOWED_DOCUMENT_MIME_TYPES
            else f
        )
    ),
]


E164PhoneNumber = Annotated[
    Union[str, phonenumbers.PhoneNumber],
    PhoneNumberValidator(number_format="E164"),
]
