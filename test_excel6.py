import openpyxl
wb = openpyxl.load_workbook('PADRAO 8 HS.xlsx', data_only=False)
sheet = wb['JAN']
sheet['N18'] = "ATESTADO"
sheet['P18'] = "ATESTADO"
print(f"P18 evaluates to: ATESTADO")
print(f"Q18 formula: {sheet['Q18'].value}")
print(f"Will Q18 break? Q18 adds P18 to Q17")
