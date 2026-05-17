from google import genai
from phoenix.otel import register
from dotenv import load_dotenv

load_dotenv()

tracer_provider = register(
    project_name="nomos-runtime",
    auto_instrument=True,
    set_global_tracer_provider=False,
    batch=True,
)

client = genai.Client()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Explain deterministic agents briefly.",
)

print(response.text)
