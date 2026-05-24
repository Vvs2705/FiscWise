import re
from typing import Optional


def validate_cpf(cpf: str) -> bool:
    """Validate a Brazilian CPF."""
    if not cpf:
        return False
    # Remove formatting characters
    cpf = re.sub(r"\D", "", cpf)
    if len(cpf) != 11:
        return False
    # Check for known invalid CPFs (all digits equal)
    if cpf in [d * 11 for d in "0123456789"]:
        return False
    # Validate first digit
    sum_1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digit_1 = (sum_1 * 10) % 11
    if digit_1 == 10:
        digit_1 = 0
    if digit_1 != int(cpf[9]):
        return False
    # Validate second digit
    sum_2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digit_2 = (sum_2 * 10) % 11
    if digit_2 == 10:
        digit_2 = 0
    if digit_2 != int(cpf[10]):
        return False
    return True


def validate_cnpj(cnpj: str) -> bool:
    """Validate a Brazilian CNPJ."""
    if not cnpj:
        return False
    # Remove formatting characters
    cnpj = re.sub(r"\D", "", cnpj)
    if len(cnpj) != 14:
        return False
    # Check for known invalid CNPJs (all digits equal)
    if cnpj in [d * 14 for d in "0123456789"]:
        return False

    # Validate first digit
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_1 = sum(int(cnpj[i]) * weights_1[i] for i in range(12))
    digit_1 = sum_1 % 11
    digit_1 = 0 if digit_1 < 2 else 11 - digit_1
    if digit_1 != int(cnpj[12]):
        return False

    # Validate second digit
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_2 = sum(int(cnpj[i]) * weights_2[i] for i in range(13))
    digit_2 = sum_2 % 11
    digit_2 = 0 if digit_2 < 2 else 11 - digit_2
    if digit_2 != int(cnpj[13]):
        return False

    return True


def validate_cpf_or_cnpj(value: str) -> bool:
    """Validate if value is a valid CPF or CNPJ."""
    if not value:
        return False
    clean_val = re.sub(r"\D", "", value)
    if len(clean_val) == 11:
        return validate_cpf(clean_val)
    elif len(clean_val) == 14:
        return validate_cnpj(clean_val)
    return False


def validate_optional_cpf_or_cnpj(value: Optional[str]) -> Optional[str]:
    """Validate optional CPF or CNPJ document string and return clean value."""
    if not value:
        return value
    if not validate_cpf_or_cnpj(value):
        raise ValueError("Invalid CPF or CNPJ document")
    return value
