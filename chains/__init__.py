from core.config import settings


def get_llm():
    provider = settings.AI_PROVIDER.lower()

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            api_key=settings.GROQ_API_KEY,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.CLAUDE_MODEL,
            temperature=0,
            api_key=settings.ANTHROPIC_API_KEY,
        )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0,
            google_api_key=settings.GOOGLE_API_KEY,
        )
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model="llama3.1", temperature=0)
    else:
        raise ValueError(f"Unsupported AI_PROVIDER: {provider}. Choose: groq, anthropic, google, ollama")
