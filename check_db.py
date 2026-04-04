import re

with open('database.py', 'r', encoding='utf-8') as f:
    text = f.read()

matches = re.findall(r'async def (get_[a-zA-Z0-9_]+).*?return await cursor\.(fetchone|fetchall)\(\)', text, re.DOTALL)
for m in matches:
    print(m[0], m[1])
