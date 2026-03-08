import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL", "http://localhost:8001")
key: str = os.getenv("SUPABASE_SERVICE_KEY", "YOUR_SUPABASE_SERVICE_KEY")

supabase: Client = create_client(url, key)
