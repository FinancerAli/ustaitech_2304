import re

with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

def patch_func(func_name, normalizer, wrap_list):
    global content
    pattern = r'(async def ' + func_name + r'\b.*?:\n(?:(?:    )+.*?\n)+?)( +)(return await cursor\.(fetchone|fetchall)\(\)\n?)'
    
    def repl(m):
        prefix = m.group(1)
        indent = m.group(2)
        fetch_call = m.group(3).strip()
        is_fetchall = 'fetchall' in fetch_call
        
        if wrap_list and is_fetchall:
            replacement = f'{indent}rows = {fetch_call}\n{indent}return [{normalizer}(r) for r in rows]\n'
        else:
            replacement = f'{indent}row = {fetch_call}\n{indent}return {normalizer}(row)\n'
        return prefix + replacement
        
    content, n = re.subn(pattern, repl, content, count=1, flags=re.DOTALL)
    print(f'Patched {func_name}: {n}')

# Categories
patch_func('get_categories', 'normalize_category', True)
patch_func('get_category', 'normalize_category', False)

# Users
patch_func('get_user', 'normalize_user', False)
patch_func('get_user_by_referral', 'normalize_user', False)
patch_func('get_all_users', 'normalize_user', True)
patch_func('get_confirmed_customers', 'normalize_user', True)
patch_func('get_confirmed_customer_detail', 'normalize_user', False)

# Coupons
patch_func('get_coupon', 'normalize_coupon', False)
patch_func('get_available_coupons_for_service', 'normalize_coupon', True)
patch_func('get_all_coupons', 'normalize_coupon', True)

# Orders
patch_func('get_order', 'normalize_order', False)
patch_func('get_user_orders', 'normalize_order', True)
patch_func('get_pending_orders', 'normalize_order', True)
patch_func('get_all_orders', 'normalize_order', True)

with open('database.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
