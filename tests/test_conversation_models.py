from imessage_data_foundry.conversations.models import Attachment, Chat, Handle, Message
from imessage_data_foundry.personas.models import IdentifierType, Persona


class TestMessageCreation:
    def test_basic_message(self):
        msg = Message(text="Hello!", date=1000000000000)
        assert msg.text == "Hello!"
        assert msg.date == 1000000000000
        assert msg.guid.startswith("p:0/")

    def test_outgoing_message(self):
        msg = Message.create_outgoing(
            text="Hello!",
            date=1000000000000,
            service="iMessage",
        )
        assert msg.is_from_me is True
        assert msg.handle_id is None
        assert msg.text == "Hello!"
        assert msg.is_sent is True
        assert msg.is_delivered is True

    def test_incoming_message(self):
        msg = Message.create_incoming(
            text="Hi there!",
            date=1000000000000,
            handle_id=1,
            service="iMessage",
        )
        assert msg.is_from_me is False
        assert msg.handle_id == 1
        assert msg.is_read is True
        assert msg.is_delivered is True

    def test_guid_unique(self):
        msg1 = Message(text="Test", date=1000)
        msg2 = Message(text="Test", date=1000)
        assert msg1.guid != msg2.guid

    def test_sms_service(self):
        msg = Message.create_outgoing(text="Hello!", date=1000, service="SMS")
        assert msg.service == "SMS"


class TestMessageDefaults:
    def test_default_values(self):
        msg = Message(text="Test", date=1000)
        assert msg.service == "iMessage"
        assert msg.is_delivered is True
        assert msg.is_sent is True
        assert msg.is_read is True
        assert msg.is_finished is True
        assert msg.is_from_me is False
        assert msg.handle_id is None
        assert msg.date_read is None
        assert msg.date_delivered is None
        assert msg.cache_roomnames is None


class TestChatCreation:
    def test_direct_chat(self):
        chat = Chat.create_direct("+15551234567", "iMessage")
        assert chat.style == 43
        assert "+15551234567" in chat.guid
        assert chat.service_name == "iMessage"
        assert chat.guid == "iMessage;-;+15551234567"
        assert chat.chat_identifier == "+15551234567"

    def test_group_chat(self):
        chat = Chat.create_group(
            display_name="Friends",
            service="iMessage",
        )
        assert chat.style == 45
        assert chat.display_name == "Friends"
        assert ";+;" in chat.guid
        assert chat.guid.startswith("iMessage;+;chat")

    def test_sms_direct_chat(self):
        chat = Chat.create_direct("+15551234567", "SMS")
        assert chat.service_name == "SMS"
        assert chat.guid.startswith("SMS;-;")

    def test_sms_group_chat(self):
        chat = Chat.create_group(service="SMS")
        assert chat.service_name == "SMS"
        assert chat.guid.startswith("SMS;+;")


class TestChatDefaults:
    def test_default_state(self):
        chat = Chat.create_direct("+15551234567")
        assert chat.state == 3
        assert chat.display_name is None
        assert chat.handle_ids == []


class TestHandleCreation:
    def test_basic_handle(self):
        handle = Handle(id="+15551234567", country="US", service="iMessage")
        assert handle.id == "+15551234567"
        assert handle.service == "iMessage"
        assert handle.country == "US"

    def test_from_phone_persona(self):
        persona = Persona(
            name="Test User",
            identifier="+15551234567",
            identifier_type=IdentifierType.PHONE,
            country_code="US",
        )
        handle = Handle.from_persona(persona)
        assert handle.id == "+15551234567"
        assert handle.country == "US"
        assert handle.service == "iMessage"

    def test_from_email_persona(self):
        persona = Persona(
            name="Test User",
            identifier="user@example.com",
            identifier_type=IdentifierType.EMAIL,
            country_code="US",
        )
        handle = Handle.from_persona(persona)
        assert handle.id == "user@example.com"
        assert handle.country is None
        assert handle.service == "iMessage"


class TestHandleDefaults:
    def test_default_values(self):
        handle = Handle(id="+15551234567")
        assert handle.country == "US"
        assert handle.service == "iMessage"
        assert handle.uncanonicalized_id is None
        assert handle.person_centric_id is None


class TestAttachmentCreation:
    def test_basic_attachment(self):
        attachment = Attachment()
        assert attachment.guid.startswith("at_0_")
        assert attachment.transfer_state == 5

    def test_with_metadata(self):
        attachment = Attachment(
            filename="/path/to/image.png",
            uti="public.png",
            mime_type="image/png",
            total_bytes=12345,
            is_outgoing=True,
        )
        assert attachment.filename == "/path/to/image.png"
        assert attachment.uti == "public.png"
        assert attachment.mime_type == "image/png"
        assert attachment.total_bytes == 12345
        assert attachment.is_outgoing is True


class TestAttachmentDefaults:
    def test_default_values(self):
        attachment = Attachment()
        assert attachment.filename is None
        assert attachment.uti is None
        assert attachment.mime_type is None
        assert attachment.total_bytes == 0
        assert attachment.is_outgoing is False
        assert attachment.created_date is None
        assert attachment.transfer_state == 5
