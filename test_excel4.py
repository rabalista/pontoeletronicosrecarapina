import openpyxl
wb = openpyxl.load_workbook('PADRAO 8 HS.xlsx', data_only=False)
sheet = wb['JAN']
for row in sheet.iter_rows(min_row=1, max_row=10, min_col=1, max_col=15):
    for cell in row:
        if cell.value:
            print(f"{cell.coordinate}: {cell.value}")
