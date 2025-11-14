"""LangChain agent setup with OpenAI and tools."""

import os

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.rag.supabase_client import SupabaseRAGClient
from app.tools.rag_tool import create_rag_tool
from app.tools.web_search import create_web_search_tool

# Load environment variables
load_dotenv()


def create_macbook_agent():
    """
    Create and configure the MacBook Air chatbot agent.

    Returns:
        Configured LangChain agent
    """
    # Initialize OpenAI LLM
    llm = ChatOpenAI(
        model="gpt-4o", temperature=0.7, streaming=True, api_key=os.getenv("OPENAI_API_KEY")
    )

    # Initialize RAG client
    rag_client = SupabaseRAGClient(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Create tools
    web_search_tool = create_web_search_tool()
    rag_tool = create_rag_tool(rag_client)

    tools = [web_search_tool, rag_tool]

    # System prompt for the agent
    system_prompt = """You are a helpful and knowledgeable assistant specialized in answering questions about the MacBook Air.

Your primary goal is to provide accurate, helpful, and up-to-date information about MacBook Air products, specially the latest model (M4).

Guidelines:
1. Use the retrieve_macbook_facts tool to access stored knowledge about MacBook Air specifications, features, and general information.
2. Use the web_search tool to find current information such as:
   - Current prices and availability
   - Latest news and updates
   - Recent reviews
   - Current promotions
3. When you have information from both sources, combine them to provide comprehensive answers.
4. Always cite your sources when possible.
5. When mentioning prices or specific information found via web_search, include the source link in markdown format. For example: "The 13-inch MacBook Air with M4 starts at $999 ([source](https://www.apple.com/...))". Extract the link from the web_search results.
6. If information conflicts between sources, prioritize the most recent information from web search for current data, but use stored facts for historical or technical specifications.
7. Be conversational and helpful, but always accurate.
8. If you're unsure about something, say so rather than guessing.
9. Be mindful of which model is being discussed, by default it'll refer to the latest model (M4), and only provide information about that model.
10. If the user asks about a specific model, use the retrieve_macbook_facts tool to access stored knowledge about that model, rewrite the query if necessary to fit the model name.
11. If the user asks about a comparison between models, use the retrieve_macbook_facts tool to access stored knowledge about the models being compared against the latest model (M4).
12. If the user asks about a feature, use the retrieve_macbook_facts tool to access stored knowledge about the feature.

Focus on providing clear, accurate, and helpful responses about MacBook Air."""

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # Create the agent
    agent = create_openai_tools_agent(llm=llm, tools=tools, prompt=prompt)

    # Create agent executor
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
