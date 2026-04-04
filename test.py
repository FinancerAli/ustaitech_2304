import asyncio
import database as db

async def test():
    await db.init_db()
    users = await db.get_all_users()
    print('Users:', len(users), 'type:', type(users[0]) if users else 'none')
    orders = await db.get_all_orders()
    print('Orders:', len(orders), 'type:', type(orders[0]) if orders else 'none')
    cats = await db.get_categories()
    print('Cats:', len(cats), 'type:', type(cats[0]) if cats else 'none')
    coupons = await db.get_all_coupons()
    print('Coupons:', len(coupons), 'type:', type(coupons[0]) if coupons else 'none')

asyncio.run(test())
