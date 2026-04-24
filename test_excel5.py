import openpyxl
wb = openpyxl.load_workbook('PADRAO 8 HS.xlsx', data_only=False)
sheet = wb['JAN']
print(f"C6: {sheet['C6'].value}")
print(f"L7: {sheet['L7'].value}")
print(f"L8: {sheet['L8'].value}")
print(f"N9: {sheet['N9'].value}")
print(f"Q4: {sheet['Q4'].value}") # saldo from year before?
