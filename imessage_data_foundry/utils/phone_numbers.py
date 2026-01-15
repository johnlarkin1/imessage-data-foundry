import phonenumbers
from faker import Faker
from phonenumbers import PhoneNumber, PhoneNumberFormat
from phonenumbers.phonenumberutil import NumberParseException

LOCALE_MAP: dict[str, str] = {
    "US": "en_US",
    "GB": "en_GB",
    "CA": "en_CA",
    "AU": "en_AU",
    "DE": "de_DE",
    "FR": "fr_FR",
    "ES": "es_ES",
    "IT": "it_IT",
    "JP": "ja_JP",
    "CN": "zh_CN",
}


def parse_phone_number(number: str, region: str = "US") -> PhoneNumber:
    """Parse a phone number string into a PhoneNumber object."""
    return phonenumbers.parse(number, region)


def format_e164(number: str | PhoneNumber, region: str = "US") -> str:
    """Format phone number to E.164 format (+15551234567)."""
    if isinstance(number, str):
        number = parse_phone_number(number, region)
    return phonenumbers.format_number(number, PhoneNumberFormat.E164)


def format_national(number: str | PhoneNumber, region: str = "US") -> str:
    """Format phone number to national format ((555) 123-4567)."""
    if isinstance(number, str):
        number = parse_phone_number(number, region)
    return phonenumbers.format_number(number, PhoneNumberFormat.NATIONAL)


def format_international(number: str | PhoneNumber, region: str = "US") -> str:
    """Format phone number to international format (+1 555-123-4567)."""
    if isinstance(number, str):
        number = parse_phone_number(number, region)
    return phonenumbers.format_number(number, PhoneNumberFormat.INTERNATIONAL)


def is_valid_phone_number(number: str, region: str = "US") -> bool:
    """Check if a phone number string is valid."""
    if not number:
        return False
    try:
        parsed = phonenumbers.parse(number, region)
        return phonenumbers.is_valid_number(parsed)
    except NumberParseException:
        return False


def get_country_code(number: str | PhoneNumber, region: str = "US") -> int:
    """Extract country code from a phone number."""
    if isinstance(number, str):
        number = parse_phone_number(number, region)
    return number.country_code or 0


def get_region_code(number: str | PhoneNumber) -> str | None:
    """Get region code (US, GB, etc.) from a phone number."""
    if isinstance(number, str):
        try:
            number = phonenumbers.parse(number, None)
        except NumberParseException:
            return None
    return phonenumbers.region_code_for_number(number)


def generate_fake_phone(region: str = "US") -> str:
    """Generate a fake phone number in E.164 format."""
    locale = LOCALE_MAP.get(region, "en_US")
    fake = Faker(locale)

    for _ in range(10):
        raw_number = fake.phone_number()
        try:
            formatted = format_e164(raw_number, region)
            if is_valid_phone_number(formatted, region):
                return formatted
        except NumberParseException:
            continue

    country_codes = {"US": "1", "GB": "44", "CA": "1", "AU": "61", "DE": "49"}
    cc = country_codes.get(region, "1")
    random_digits = fake.random_number(digits=10, fix_len=True)
    return f"+{cc}{random_digits}"


def normalize_identifier(identifier: str, region: str = "US") -> str:
    """Normalize a phone number or email identifier."""
    identifier = identifier.strip()
    if "@" in identifier:
        return identifier.lower()
    try:
        return format_e164(identifier, region)
    except NumberParseException:
        return identifier
