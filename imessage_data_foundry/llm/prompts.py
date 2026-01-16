import json
from textwrap import dedent

from imessage_data_foundry.llm.models import GeneratedMessage, GeneratedPersona, PersonaConstraints


class PromptTemplates:
    """Centralized prompt templates for LLM generation."""

    @classmethod
    def persona_generation(cls, constraints: PersonaConstraints | None, count: int = 1) -> str:
        constraint_text = cls._format_constraints(constraints) if constraints else ""
        schema_str = json.dumps(GeneratedPersona.model_json_schema(), indent=2)

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
            - 3-5 UNIQUE topics they naturally discuss

            CRITICAL: Each persona must have DIFFERENT topics_of_interest from the others.
            Avoid overlap - if one persona talks about sports, others should NOT.
            Example topic categories to diversify across: tech, cooking, fitness, movies,
            travel, music, gaming, books, art, science, fashion, pets, outdoor activities,
            career/work, parenting, investing, home improvement, photography, gardening.

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

        participant_ids = [p["id"] for p in persona_descriptions]
        id_list = ", ".join(f'"{pid}"' for pid in participant_ids)

        return dedent(f"""
            Generate {count} text messages between these people:

            {personas_text}

            {context_text}
            {seed_text}

            RULES:
            - ALL messages MUST be in English only
            - Each sender_id must be one of: {id_list}
            - Match each person's writing style
            - Vary message lengths naturally
            - Alternate between participants

            Return ONLY a JSON array, no other text:
            [{{"sender_id": "...", "text": "...", "is_from_me": false}}, ...]

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
