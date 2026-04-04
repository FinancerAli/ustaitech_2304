import asyncio
import database as db
import traceback

async def test():
    try:
        orders = await db.get_all_orders()
        print('Orders:', len(orders))
    except Exception as e:
        traceback.print_exc()

asyncio.run(test())
