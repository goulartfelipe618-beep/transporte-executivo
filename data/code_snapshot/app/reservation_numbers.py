"""Numeracao de reservas — sem Tkinter (runtime headless / rede comercial)."""


def next_reservation_number(app):
    return next_reservation_numbers(app, 1)[0]


def next_reservation_numbers(app, count=1):
    numbers = []
    for item in app.reservations:
        try:
            numbers.append(int(str(item.get("numero", "")).replace("#", "")))
        except (ValueError, AttributeError):
            pass
    start = max(numbers, default=1000) + 1
    return [f"#{start + offset}" for offset in range(count)]
