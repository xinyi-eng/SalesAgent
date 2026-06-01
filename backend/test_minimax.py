# Test MiniMax API key
import os
os.chdir('C:/Users/zsndz/Desktop/SalesAgent/backend')

# Load env
from pathlib import Path
_env_path = Path('.env')
if _env_path.exists():
    with open(_env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value
                print(f"Set {key}={value[:20]}...")

from app.config import settings
print(f"Settings MINIMAX_API_KEY: {settings.MINIMAX_API_KEY[:20] if settings.MINIMAX_API_KEY else 'None'}...")

# Test MiniMax service
import asyncio
from app.services.llm import get_minimax_service

async def test():
    service = get_minimax_service()
    print(f"Service api_key: {service.api_key[:20] if service.api_key else 'None'}...")
    print(f"Has api_key: {bool(service.api_key)}")

    if service.api_key:
        print("Testing chat...")
        try:
            response = await service.chat([{"role": "user", "content": "hi"}])
            print(f"Chat response: {response[:100]}...")
        except Exception as e:
            print(f"Chat error: {e}")

asyncio.run(test())