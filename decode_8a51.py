import json

with open('scratch/char_table.json', 'r') as f:
    table = json.load(f)

# The table has keys like "3001", so we need to convert to int and find the value
inv_table = {}
for k, v in table.items():
    inv_table[int(k, 16)] = v

data = [0x0144, 0x0114, 0x0092, 0x03FE, 0x03FE, 0x03FE, 0x03FE]

res = ""
for w in data:
    if w in inv_table:
        res += inv_table[w]
    else:
        res += f"[{w:04X}]"

print(f"Decoded: {res}")
