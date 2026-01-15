import pytest
from phonenumbers.phonenumberutil import NumberParseException

from imessage_data_foundry.utils.phone_numbers import (
    format_e164,
    format_international,
    format_national,
    generate_fake_phone,
    get_country_code,
    get_region_code,
    is_valid_phone_number,
    normalize_identifier,
    parse_phone_number,
)


class TestParsePhoneNumber:
    def test_parse_e164_us(self):
        result = parse_phone_number("+15551234567", "US")
        assert result.country_code == 1
        assert result.national_number == 5551234567

    def test_parse_local_format(self):
        result = parse_phone_number("(555) 123-4567", "US")
        assert result.country_code == 1

    def test_parse_uk_number(self):
        result = parse_phone_number("+442071234567", "GB")
        assert result.country_code == 44

    def test_invalid_raises(self):
        with pytest.raises(NumberParseException):
            parse_phone_number("invalid", "US")


class TestFormatE164:
    def test_from_local(self):
        result = format_e164("(555) 123-4567", "US")
        assert result == "+15551234567"

    def test_from_phone_number_object(self):
        parsed = parse_phone_number("+15551234567", "US")
        result = format_e164(parsed, "US")
        assert result == "+15551234567"

    def test_uk_number(self):
        result = format_e164("+442071234567", "GB")
        assert result == "+442071234567"


class TestFormatNational:
    def test_us_number(self):
        result = format_national("+15551234567", "US")
        assert "555" in result
        assert "123" in result
        assert "4567" in result


class TestFormatInternational:
    def test_us_number(self):
        result = format_international("+15551234567", "US")
        assert result.startswith("+1")


class TestIsValidPhoneNumber:
    def test_valid_e164(self):
        # Use a real-looking US number (555 is fictional and invalid)
        assert is_valid_phone_number("+12025551234", "US") is True

    def test_invalid_string(self):
        assert is_valid_phone_number("invalid", "US") is False

    def test_empty_string(self):
        assert is_valid_phone_number("", "US") is False

    def test_fictional_555_invalid(self):
        # 555-0100 to 555-0199 are reserved for fiction
        assert is_valid_phone_number("+15550100", "US") is False


class TestGetCountryCode:
    def test_us_number(self):
        result = get_country_code("+15551234567", "US")
        assert result == 1

    def test_uk_number(self):
        result = get_country_code("+442071234567", "GB")
        assert result == 44


class TestGetRegionCode:
    def test_us_number(self):
        # Use valid US number (202 is Washington DC area code)
        result = get_region_code("+12025551234")
        assert result == "US"

    def test_uk_number(self):
        result = get_region_code("+442071234567")
        assert result == "GB"

    def test_invalid_returns_none(self):
        result = get_region_code("invalid")
        assert result is None


class TestGenerateFakePhone:
    def test_returns_e164_format(self):
        result = generate_fake_phone("US")
        assert result.startswith("+")

    def test_reasonable_length(self):
        result = generate_fake_phone("US")
        assert len(result) >= 10

    def test_different_regions(self):
        us_phone = generate_fake_phone("US")
        # Just verify it doesn't crash for different regions
        gb_phone = generate_fake_phone("GB")
        assert us_phone.startswith("+")
        assert gb_phone.startswith("+")


class TestNormalizeIdentifier:
    def test_phone_to_e164(self):
        result = normalize_identifier("(555) 123-4567", "US")
        assert result == "+15551234567"

    def test_email_lowercase(self):
        result = normalize_identifier("Test@Example.com", "US")
        assert result == "test@example.com"

    def test_already_e164(self):
        result = normalize_identifier("+15551234567", "US")
        assert result == "+15551234567"

    def test_strips_whitespace(self):
        result = normalize_identifier("  test@example.com  ", "US")
        assert result == "test@example.com"

    def test_invalid_phone_returned_as_is(self):
        result = normalize_identifier("invalid", "US")
        assert result == "invalid"
