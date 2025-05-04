import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_sql(question, schema):
    prompt = f"""
You are a helpful assistant that writes SQL queries.

Given this schema:
{schema}

And this question:
{question}

Return only the SQL query.
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()
