import json
from textwrap import dedent

from imessage_data_foundry.llm.models import GeneratedMessage, PersonaConstraints
from imessage_data_foundry.personas.models import (
    CommunicationFrequency,
    EmojiUsage,
    ResponseTime,
    VocabularyLevel,
)

PERSONA_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Full name of the persona"},
        "personality": {"type": "string", "description": "Personality description (2-3 sentences)"},
        "writing_style": {
            "type": "string",
            "description": "How they write texts (formal, casual, uses slang, etc.)",
        },
        "relationship": {"type": "string", "description": "Relationship to the user"},
        "communication_frequency": {
            "type": "string",
            "enum": [e.value for e in CommunicationFrequency],
        },
        "typical_response_time": {"type": "string", "enum": [e.value for e in ResponseTime]},
        "emoji_usage": {"type": "string", "enum": [e.value for e in EmojiUsage]},
        "vocabulary_level": {"type": "string", "enum": [e.value for e in VocabularyLevel]},
        "topics_of_interest": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-5 topics they often discuss",
        },
    },
    "required": [
        "name",
        "personality",
        "writing_style",
        "relationship",
        "communication_frequency",
        "typical_response_time",
        "emoji_usage",
        "vocabulary_level",
        "topics_of_interest",
    ],
}


class PromptTemplates:
    """Centralized prompt templates for LLM generation."""

    @classmethod
    def persona_generation(cls, constraints: PersonaConstraints | None, count: int = 1) -> str:
        constraint_text = cls._format_constraints(constraints) if constraints else ""
        schema_str = json.dumps(PERSONA_JSON_SCHEMA, indent=2)

        return dedent(f"""
            You are creating realistic persona(s) for a text messaging simulation.

            Create {count} unique persona(s) that would be contacts in someone's phone.
            Each persona should feel like a real person with distinct texting habits.

            {constraint_text}

            Each persona MUST have:
            - A realistic full name
            - A distinct personality that affects their texting behavior
            - A specific writing style (formal, casual, uses slang, abbreviations, etc.)
            - Defined emoji usage patterns matching their personality
            - 3-5 topics they naturally discuss

            IMPORTANT: Return ONLY valid JSON with no additional text or explanation.

            JSON Schema to follow:
            {schema_str}

            {"Return a JSON array of " + str(count) + " persona objects." if count > 1 else "Return a single JSON object (not an array)."}
        """).strip()

    @classmethod
    def message_generation(
        cls,
        persona_descriptions: list[dict[str, str]],
        context: list[GeneratedMessage],
        count: int,
        seed: str | None = None,
    ) -> str:
        personas_text = cls._format_persona_descriptions(persona_descriptions)
        context_text = (
            cls._format_context(context) if context else "This is the START of the conversation."
        )
        seed_text = f"\nConversation theme/topic: {seed}" if seed else ""

        return dedent(f"""
            You are simulating a realistic text message conversation between people.

            PARTICIPANTS:
            {personas_text}

            CONVERSATION CONTEXT:
            {context_text}
            {seed_text}

            Generate the next {count} messages in this conversation.

            IMPORTANT GUIDELINES:
            - Each message should feel like a genuine text message
            - Match each sender's personality, writing style, and emoji usage
            - Vary message lengths naturally (some short "lol ok", some longer)
            - Include natural conversation patterns (questions, responses, topic shifts)
            - The "self" persona (is_from_me=true) should be one participant
            - Alternate between participants naturally, not strictly back-and-forth

            IMPORTANT: Return ONLY valid JSON with no additional text.

            Return a JSON array of message objects:
            [
              {{"sender_id": "<persona_id>", "text": "<message text>", "is_from_me": <boolean>}},
              ...
            ]

            Generate exactly {count} messages.
        """).strip()

    @classmethod
    def _format_constraints(cls, constraints: PersonaConstraints) -> str:
        parts = ["CONSTRAINTS:"]

        if constraints.relationship:
            parts.append(f"- Relationship to user: {constraints.relationship}")
        if constraints.communication_frequency:
            parts.append(f"- Communication frequency: {constraints.communication_frequency.value}")
        if constraints.vocabulary_level:
            parts.append(f"- Vocabulary level: {constraints.vocabulary_level.value}")
        if constraints.emoji_usage:
            parts.append(f"- Emoji usage: {constraints.emoji_usage.value}")
        if constraints.typical_response_time:
            parts.append(f"- Response time: {constraints.typical_response_time.value}")
        if constraints.age_range:
            parts.append(f"- Age range: {constraints.age_range[0]}-{constraints.age_range[1]}")
        if constraints.topics:
            parts.append(f"- Topics of interest: {', '.join(constraints.topics)}")
        if constraints.personality_traits:
            parts.append(f"- Personality traits: {', '.join(constraints.personality_traits)}")

        return "\n".join(parts) if len(parts) > 1 else ""

    @classmethod
    def _format_persona_descriptions(cls, personas: list[dict[str, str]]) -> str:
        parts = []
        for p in personas:
            is_self = p.get("is_self", False)
            self_marker = (
                " (THIS IS YOU - messages from this persona have is_from_me=true)"
                if is_self
                else ""
            )
            parts.append(
                f"- ID: {p['id']}{self_marker}\n"
                f"  Name: {p['name']}\n"
                f"  Personality: {p.get('personality', 'Not specified')}\n"
                f"  Writing style: {p.get('writing_style', 'casual')}\n"
                f"  Emoji usage: {p.get('emoji_usage', 'light')}\n"
                f"  Topics: {p.get('topics', 'general')}"
            )
        return "\n".join(parts)

    @classmethod
    def _format_context(cls, context: list[GeneratedMessage]) -> str:
        if not context:
            return "No previous messages."

        parts = ["Recent messages:"]
        for msg in context:
            sender = "You" if msg.is_from_me else f"[{msg.sender_id}]"
            parts.append(f"  {sender}: {msg.text}")
        return "\n".join(parts)
