import re

def clean_cpf_cnpj(value: str) -> str:
    return re.sub(r"\D", "", value)

def validate_cpf(cpf: str) -> bool:
    cpf = clean_cpf_cnpj(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    # Check first digit
    sum_val = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digit_1 = (sum_val * 10 % 11) % 10

    # Check second digit
    sum_val = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digit_2 = (sum_val * 10 % 11) % 10

    return int(cpf[9]) == digit_1 and int(cpf[10]) == digit_2

def validate_cnpj(cnpj: str) -> bool:
    cnpj = clean_cpf_cnpj(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    # First digit weights: 5,4,3,2,9,8,7,6,5,4,3,2
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_val = sum(int(cnpj[i]) * weights_1[i] for i in range(12))
    digit_1 = 11 - (sum_val % 11)
    if digit_1 >= 10:
        digit_1 = 0

    # Second digit weights: 6,5,4,3,2,9,8,7,6,5,4,3,2
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_val = sum(int(cnpj[i]) * weights_2[i] for i in range(13))
    digit_2 = 11 - (sum_val % 11)
    if digit_2 >= 10:
        digit_2 = 0

    return int(cnpj[12]) == digit_1 and int(cnpj[13]) == digit_2

def validate_cpf_cnpj(value: str) -> bool:
    clean_val = clean_cpf_cnpj(value)
    if len(clean_val) == 11:
        return validate_cpf(clean_val)
    elif len(clean_val) == 14:
        return validate_cnpj(clean_val)
    return False
