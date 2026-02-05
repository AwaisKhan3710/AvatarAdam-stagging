"""LLM Service using OpenRouter with GPT models."""

from openai import AsyncOpenAI

from app.core.config import settings


class LLMService:
    """Service for interacting with LLMs via OpenRouter."""

    def __init__(self):
        """Initialize OpenRouter client."""
        self.client = AsyncOpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
        )
        self.model = settings.OPENROUTER_MODEL

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        conversation_history: list[dict] | None = None,
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: User's message/prompt
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            conversation_history: Optional list of previous messages

        Returns:
            Generated response text
        """
        messages = []

        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)

        # Add current user message
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content or ""

    async def generate_with_context(
        self,
        query: str,
        context: str,
        mode: str = "training",
        conversation_history: list[dict] | None = None,
    ) -> str:
        """
        Generate a response with RAG context.

        Args:
            query: User's question
            context: Retrieved context from RAG
            mode: "training" (AI as trainer) or "roleplay" (AI as customer)
            conversation_history: Optional conversation history

        Returns:
            Generated response
        """
        if mode == "training":
            system_prompt = """You are Adam Marburger, an expert F&I trainer with decades of experience in the automotive industry.

IMPORTANT: Your response will be converted to speech. Follow these rules:
- Use plain text only, no markdown, no bullet points, no numbered lists
- No asterisks, no bold, no italics, no special formatting
- Write in natural conversational sentences
- Keep responses concise and direct

Your role is to answer questions based on the training materials and give practical advice.
Be direct, specific, and supportive.

Training Materials:
{context}

If no context is provided, use your general F&I expertise."""
        else:  # roleplay
            system_prompt = """You are a realistic customer at an automotive dealership who just purchased or is about to purchase a vehicle.
The person you are talking to is a dealer/F&I manager in the finance office.

IMPORTANT: Your response will be converted to speech. Follow these rules:
- Use plain text only, no markdown, no bullet points, no numbered lists
- No asterisks, no bold, no italics, no special formatting
- Write in natural conversational sentences
- Keep responses concise and realistic
- ONLY respond as the customer - never break character or give advice

BEHAVIOR:
- If this is the start of conversation, introduce yourself and express interest in what protection products or services are available
- Ask what F&I products they offer (extended warranties, GAP insurance, paint protection, etc.)
- Present realistic objections and concerns when products are pitched
- Be skeptical but fair - ask about pricing, value, and whether you really need it
- React naturally to the dealer's sales techniques

{context_section}

Vary your personality - sometimes price-focused, sometimes value-focused, sometimes time-pressured."""

        # For roleplay, include context about common objections and product knowledge
        if context:
            context_section = f"""Reference Materials (use these to create realistic scenarios and objections):
{context}

Use the objection handling materials to present common customer concerns.
Use product knowledge to ask informed questions about the products being offered."""
        else:
            context_section = "No specific dealership materials provided - use general F&I customer scenarios."

        formatted_system = (
            system_prompt.format(context=context)
            if mode == "training"
            else system_prompt.format(context_section=context_section)
        )

        return await self.generate(
            prompt=query,
            system_prompt=formatted_system,
            temperature=0.7 if mode == "training" else 0.8,
            max_tokens=800,
            conversation_history=conversation_history,
        )

    async def classify_query_topics(
        self,
        query: str,
        available_topics: list[str],
    ) -> list[str]:
        """
        Classify which knowledge base topics are relevant to a query.

        Args:
            query: User's question
            available_topics: List of available topic categories

        Returns:
            List of relevant topic names
        """
        system_prompt = f"""You are a query classifier. Given a question, determine which knowledge base topics are most relevant.

Available topics: {", ".join(available_topics)}

Respond with ONLY a comma-separated list of relevant topics (1-3 topics max).
Example: "objection_handling, playbooks"
"""

        response = await self.generate(
            prompt=f"Question: {query}\n\nRelevant topics:",
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=50,
        )

        # Parse response to get topic list (case-insensitive matching)
        topics = [t.strip().lower() for t in response.split(",")]
        # Create lowercase mapping for available topics
        available_topics_lower = {t.lower(): t for t in available_topics}
        # Filter to only valid topics, returning original case
        return [available_topics_lower[t] for t in topics if t in available_topics_lower]


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get or create LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
