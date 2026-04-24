import openpyxl
wb = openpyxl.load_workbook('PADRAO 8 HS.xlsx', data_only=False)
sheet = wb['JAN']
print(f"L14 formula: {sheet['L14'].value}")
print(f"M14 formula: {sheet['M14'].value}")
