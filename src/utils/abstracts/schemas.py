from typing import Annotated, Union

import phonenumbers
from pydantic_extra_types.phone_numbers import PhoneNumberValidator

E164PhoneNumber = Annotated[
    Union[str, phonenumbers.PhoneNumber],
    PhoneNumberValidator(number_format="E164"),
]
