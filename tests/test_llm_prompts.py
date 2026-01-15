from imessage_data_foundry.llm.models import GeneratedMessage, GeneratedPersona, PersonaConstraints
from imessage_data_foundry.llm.prompts import PromptTemplates
from imessage_data_foundry.personas.models import (
    CommunicationFrequency,
    EmojiUsage,
    VocabularyLevel,
)


class TestPersonaJsonSchema:
    def test_schema_has_required_fields(self):
        schema = GeneratedPersona.model_json_schema()
        assert "properties" in schema
        assert "required" in schema

    def test_schema_required_fields(self):
        schema = GeneratedPersona.model_json_schema()
        required = schema["required"]
        assert "name" in required
        assert "personality" in required
        assert "writing_style" in required
        assert "relationship" in required

    def test_schema_has_enum_definitions(self):
        schema = GeneratedPersona.model_json_schema()
        assert "$defs" in schema
        defs = schema["$defs"]
        assert "CommunicationFrequency" in defs
        assert "EmojiUsage" in defs
        assert "VocabularyLevel" in defs
        assert "ResponseTime" in defs


class TestPersonaGenerationPrompt:
    def test_basic_prompt(self):
        prompt = PromptTemplates.persona_generation(None, count=1)
        assert "persona" in prompt.lower()
        assert "JSON" in prompt
        assert "1 unique" in prompt or "single" in prompt.lower()

    def test_multiple_personas(self):
        prompt = PromptTemplates.persona_generation(None, count=3)
        assert "3" in prompt
        assert "array" in prompt.lower()

    def test_with_constraints(self):
        constraints = PersonaConstraints(
            relationship="family",
            vocabulary_level=VocabularyLevel.SOPHISTICATED,
        )
        prompt = PromptTemplates.persona_generation(constraints, count=1)
        assert "family" in prompt
        assert "sophisticated" in prompt

    def test_with_all_constraints(self):
        constraints = PersonaConstraints(
            relationship="friend",
            communication_frequency=CommunicationFrequency.HIGH,
            emoji_usage=EmojiUsage.HEAVY,
            vocabulary_level=VocabularyLevel.SIMPLE,
            age_range=(20, 30),
            topics=["music", "movies"],
            personality_traits=["funny", "outgoing"],
        )
        prompt = PromptTemplates.persona_generation(constraints, count=1)
        assert "friend" in prompt
        assert "high" in prompt
        assert "heavy" in prompt
        assert "20-30" in prompt
        assert "music" in prompt
        assert "funny" in prompt

    def test_includes_json_schema(self):
        prompt = PromptTemplates.persona_generation(None, count=1)
        assert "type" in prompt
        assert "properties" in prompt or "schema" in prompt.lower()


class TestMessageGenerationPrompt:
    def test_basic_prompt(self):
        personas = [
            {"id": "p1", "name": "Alice", "is_self": False},
            {"id": "p2", "name": "Bob", "is_self": True},
        ]
        prompt = PromptTemplates.message_generation(personas, [], count=10)
        assert "Alice" in prompt
        assert "Bob" in prompt
        assert "10" in prompt

    def test_with_context(self):
        personas = [
            {"id": "p1", "name": "Alice", "is_self": False},
            {"id": "p2", "name": "Bob", "is_self": True},
        ]
        context = [
            GeneratedMessage(text="Hey!", sender_id="p1", is_from_me=False),
            GeneratedMessage(text="Hi there!", sender_id="p2", is_from_me=True),
        ]
        prompt = PromptTemplates.message_generation(personas, context, count=5)
        assert "Hey!" in prompt
        assert "Hi there!" in prompt

    def test_with_seed(self):
        personas = [
            {"id": "p1", "name": "Alice", "is_self": False},
        ]
        prompt = PromptTemplates.message_generation(
            personas, [], count=10, seed="planning a birthday party"
        )
        assert "birthday party" in prompt

    def test_self_persona_marked(self):
        personas = [
            {"id": "p1", "name": "Alice", "is_self": False},
            {"id": "p2", "name": "Bob", "is_self": True},
        ]
        prompt = PromptTemplates.message_generation(personas, [], count=5)
        assert "is_from_me=true" in prompt.lower() or "THIS IS YOU" in prompt

    def test_empty_context(self):
        personas = [{"id": "p1", "name": "Alice", "is_self": False}]
        prompt = PromptTemplates.message_generation(personas, [], count=5)
        assert "START" in prompt or "No previous" in prompt

    def test_includes_json_format(self):
        personas = [{"id": "p1", "name": "Alice", "is_self": False}]
        prompt = PromptTemplates.message_generation(personas, [], count=5)
        assert "sender_id" in prompt
        assert "text" in prompt
        assert "is_from_me" in prompt


class TestFormatConstraints:
    def test_empty_constraints(self):
        constraints = PersonaConstraints()
        result = PromptTemplates._format_constraints(constraints)
        assert result == ""

    def test_single_constraint(self):
        constraints = PersonaConstraints(relationship="friend")
        result = PromptTemplates._format_constraints(constraints)
        assert "friend" in result
        assert "CONSTRAINTS" in result

    def test_multiple_constraints(self):
        constraints = PersonaConstraints(
            relationship="family",
            vocabulary_level=VocabularyLevel.SOPHISTICATED,
        )
        result = PromptTemplates._format_constraints(constraints)
        assert "family" in result
        assert "sophisticated" in result


class TestFormatPersonaDescriptions:
    def test_single_persona(self):
        personas = [
            {
                "id": "p1",
                "name": "Alice",
                "personality": "Friendly",
                "writing_style": "casual",
                "emoji_usage": "light",
                "topics": "music, movies",
                "is_self": False,
            }
        ]
        result = PromptTemplates._format_persona_descriptions(personas)
        assert "p1" in result
        assert "Alice" in result
        assert "Friendly" in result

    def test_self_persona_marked(self):
        personas = [
            {"id": "self", "name": "Me", "is_self": True},
        ]
        result = PromptTemplates._format_persona_descriptions(personas)
        assert "THIS IS YOU" in result


class TestFormatContext:
    def test_empty_context(self):
        result = PromptTemplates._format_context([])
        assert "No previous" in result

    def test_with_messages(self):
        context = [
            GeneratedMessage(text="Hello", sender_id="p1", is_from_me=False),
            GeneratedMessage(text="Hi!", sender_id="p2", is_from_me=True),
        ]
        result = PromptTemplates._format_context(context)
        assert "Hello" in result
        assert "Hi!" in result
        assert "You" in result
