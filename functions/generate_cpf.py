import random


def _calculate_digit(digits, weights):
    total = sum(value * weight for value, weight in zip(digits, weights))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


def _format_cpf(digits, with_punctuation):
    if not with_punctuation:
        return "".join(str(value) for value in digits)
    return (
        f"{digits[0]}{digits[1]}{digits[2]}."
        f"{digits[3]}{digits[4]}{digits[5]}."
        f"{digits[6]}{digits[7]}{digits[8]}-"
        f"{digits[9]}{digits[10]}"
    )


def generate_cpf(with_punctuation=True):
    base = [random.randint(0, 9) for _ in range(9)]
    first_digit = _calculate_digit(base, list(range(10, 1, -1)))
    second_digit = _calculate_digit(base + [first_digit], list(range(11, 1, -1)))
    cpf_digits = base + [first_digit, second_digit]
    return _format_cpf(cpf_digits, with_punctuation)


def generate_cpf_to_clipboard(root, with_punctuation=True):
    value = generate_cpf(with_punctuation=with_punctuation)
    root.clipboard_clear()
    root.clipboard_append(value)
    root.update_idletasks()
    return value
