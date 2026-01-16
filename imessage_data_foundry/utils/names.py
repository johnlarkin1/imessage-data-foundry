def parse_name(name: str) -> tuple[str | None, str | None, str | None]:
    """Parse a full name into (first_name, middle_name, last_name).

    Examples:
        "John" -> ("John", None, None)
        "John Doe" -> ("John", None, "Doe")
        "John Michael Doe" -> ("John", "Michael", "Doe")
        "John Paul Michael Doe" -> ("John", "Paul Michael", "Doe")
        "" -> (None, None, None)
    """
    parts = name.strip().split()
    if len(parts) == 0:
        return None, None, None
    if len(parts) == 1:
        return parts[0], None, None
    if len(parts) == 2:
        return parts[0], None, parts[1]
    return parts[0], " ".join(parts[1:-1]), parts[-1]
