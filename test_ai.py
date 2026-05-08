import asyncio
from ai_agent import _ask
async def main():
    print('Testing AI...')
    res = await _ask('Salom')
    print('Result:', res)
asyncio.run(main())
