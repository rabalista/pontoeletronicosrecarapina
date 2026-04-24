import openpyxl
wb = openpyxl.load_workbook('PADRAO 8 HS.xlsx', data_only=False)
sheet = wb['JAN']
print(f"K6: {sheet['K6'].value}")
print(f"L7: {sheet['L7'].value}")
print(f"A14: {sheet['A14'].value}")
print(f"A13: {sheet['A13'].value}")
print(f"B14: {sheet['B14'].value}")

# Check columns F, G, H, I, J, K keys
print(f"F13: {sheet['F13'].value}")
print(f"G13: {sheet['G13'].value}")
print(f"H13: {sheet['H13'].value}")
print(f"I13: {sheet['I13'].value}")
print(f"J13: {sheet['J13'].value}")
print(f"K13: {sheet['K13'].value}")
