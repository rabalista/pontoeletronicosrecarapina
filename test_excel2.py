import openpyxl
wb = openpyxl.load_workbook('PADRAO 8 HS.xlsx', data_only=False)
for name in wb.sheetnames:
    sheet = wb[name]
    print(f"Sheet {name}: K6={sheet['K6'].value}")
