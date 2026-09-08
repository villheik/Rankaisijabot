def fmt_coins(n: int) -> str:
    if n >= 10_000_000_000:
        exp = len(str(int(n))) - 1
        mantissa = n / 10**exp
        rounded = round(mantissa, 1)
        if rounded == int(rounded):
            return f"{int(rounded)}e{exp}"
        return f"{rounded}e{exp}"
    return f"{n:,}".replace(",", " ")
