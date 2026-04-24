import openpyxl
wb = openpyxl.load_workbook('PADRAO 8 HS.xlsx', data_only=False)
sheet = wb['FEV']
print(f"B14: {sheet['B14'].value}")
print(f"B41: {sheet['B41'].value}") # 28
print(f"B44: {sheet['B44'].value}") # 31
print(f"L41: {sheet['L41'].value}")
print(f"L44: {sheet['L44'].value}")
