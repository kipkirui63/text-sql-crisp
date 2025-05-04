# langchain_utils.py
import os
from langchain.chains import SQLDatabaseChain
from langchain.chat_models import ChatOpenAI
from langchain.sql_database import SQLDatabase
from dotenv import load_dotenv

load_dotenv()

def get_langchain_sql_chain(db_path):
    # Build SQLite database URL
    db_uri = f"sqlite:///{db_path}"

    # Create SQLDatabase object
    db = SQLDatabase.from_uri(db_uri)

    # Initialize OpenAI LLM
    llm = ChatOpenAI(
        temperature=0,
        model="gpt-4",  # or "gpt-3.5-turbo"
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    # Create the SQLDatabaseChain
    chain = SQLDatabaseChain.from_llm(
        llm=llm,
        db=db,
        verbose=True,
        return_intermediate_steps=False
    )

    return chain
