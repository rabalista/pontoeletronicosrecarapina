import codecs

with codecs.open('app.py', 'r', 'utf-8') as f:
    text = f.read()

idx1 = text.find('        if target_user_id:')
idx2 = text.find('        else:\n            wb.remove(wb.active)')

safe_logic = """        if target_user_id:
            try:
                user_records = list(rows)
                user_records.reverse() # chronological
                
                target_mat = rf(user_records[0], 'matricula') if user_records else None
                user_workload = workload_map.get(target_mat, '40h') or '40h'
                daily_hours = 8
                if '30h' in str(user_workload): daily_hours = 6
                elif '50h' in str(user_workload): daily_hours = 10
                user_cargo = cargo_map.get(target_mat, 'xxx')
                user_name = rf(user_records[0], 'name') if user_records else "Desconhecido"
                
                # Determine year
                m_year = datetime.datetime.now().year
                if user_records:
                    ts = rf(user_records[-1], 'timestamp')
                    if ts:
                        dtt = ts if isinstance(ts, datetime.datetime) else datetime.datetime.strptime(str(ts).split('.')[0], '%Y-%m-%d %H:%M:%S')
                        m_year = dtt.year
                    
                months_data = {}
                for r in user_records:
                    ts = rf(r, 'timestamp')
                    if not ts: continue
                    dt = ts if isinstance(ts, datetime.datetime) else datetime.datetime.strptime(str(ts).split('.')[0], '%Y-%m-%d %H:%M:%S')
                    if dt.year != m_year: continue # Export only one year per file
                    month_key = dt.strftime('%Y-%m')
                    if month_key not in months_data: months_data[month_key] = {"days": {}}
                    
                    day_key = dt.strftime('%Y-%m-%d')
                    if day_key not in months_data[month_key]["days"]: months_data[month_key]["days"][day_key] = []
                    months_data[month_key]["days"][day_key].append({'type': rf(r, 'record_type'), 'time': dt})

                import os, calendar, traceback
                try:
                    base_d = os.path.abspath(os.path.dirname(__file__))
                    template_path = os.path.join(base_d, "PADRAO 8 HS.xlsx")
                    wb = openpyxl.load_workbook(template_path)
                except Exception as ex_open:
                    with open(os.path.join(base_d, "backend.log"), "a") as flog: flog.write(f"\\nError loading template: {ex_open}\\n")
                    wb = openpyxl.Workbook() # Fallback if template missing

                month_names = ["JAN", "FEV", "MAR", "ABR", "MAIO", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
                
                for m_idx, m_name in enumerate(month_names):
                    m_num = m_idx + 1
                    if m_name in wb.sheetnames:
                        ws = wb[m_name]
                        ws['K6'] = datetime.datetime(m_year, m_num, 1)
                        ws['C6'] = user_name
                        ws['C7'] = user_cargo
                        ws['L10'] = target_mat
                        ws['L7'] = datetime.time(daily_hours, 0)
                        ws['N9'] = m_year
                        
                        m_key = f"{m_year}-{m_num:02d}"
                        month_data = months_data.get(m_key, {"days": {}})
                        num_days = calendar.monthrange(m_year, m_num)[1]
                        
                        for d_idx in range(1, num_days + 1):
                            row_idx = 13 + d_idx
                            d_key_str = f"{m_year}-{m_num:02d}-{d_idx:02d}"
                            punches = month_data["days"].get(d_key_str, [])
                            
                            has_atestado = False
                            has_abono = False
                            has_comp = False
                            ent_m, sai_m, ent_t, sai_t, ent_x, sai_x = None, None, None, None, None, None
                            
                            if len(punches) > 0:
                                punches.sort(key=lambda x: x['time'])
                                for p in punches:
                                    t_str = (p['type'] or "").lower()
                                    t_val = p['time'].time() if isinstance(p['time'], datetime.datetime) else None
                                    if not t_val: continue
                                    
                                    if 'atestado' in t_str: has_atestado = True
                                    elif 'abono' in t_str: has_abono = True
                                    elif 'compensação' in t_str or 'compensacao' in t_str:
                                        has_comp = True
                                        if not ent_x: ent_x = t_val
                                        elif not sai_x: sai_x = t_val
                                    elif 'entrada' in t_str:
                                        if ent_x and not sai_x: sai_x = t_val
                                        elif not ent_m: ent_m = t_val
                                    elif ('saída almoço' in t_str or 'saida almoco' in t_str) and not sai_m: sai_m = t_val
                                    elif ('volta almoço' in t_str or 'volta almoco' in t_str) and not ent_t: ent_t = t_val
                                    elif ('saída' in t_str and not 'almo' in t_str):
                                        if not sai_m and not ent_t: sai_m = t_val
                                        elif not sai_t: sai_t = t_val
                            
                            if has_atestado or has_abono:
                                val_str = "ATESTADO" if has_atestado else "ABONO"
                                ws.cell(row=row_idx, column=12, value=val_str)
                                ws.cell(row=row_idx, column=13, value=val_str)
                                ws.cell(row=row_idx, column=14, value=val_str)
                                ws.cell(row=row_idx, column=16, value=0)
                            else:
                                if ent_m: ws.cell(row=row_idx, column=6, value=ent_m).number_format = 'hh:mm:ss'
                                if sai_m: ws.cell(row=row_idx, column=7, value=sai_m).number_format = 'hh:mm:ss'
                                if ent_t: ws.cell(row=row_idx, column=8, value=ent_t).number_format = 'hh:mm:ss'
                                if sai_t: ws.cell(row=row_idx, column=9, value=sai_t).number_format = 'hh:mm:ss'
                                if ent_x: ws.cell(row=row_idx, column=10, value=ent_x).number_format = 'hh:mm:ss'
                                if sai_x: ws.cell(row=row_idx, column=11, value=sai_x).number_format = 'hh:mm:ss'
            except Exception as e_main:
                import traceback, os
                with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "backend.log"), "a") as flog:
                    flog.write(f"\\nCRITICAL EXCEL ERROR:\\n{traceback.format_exc()}\\n")
                raise e_main"""

new_text = text[:idx1] + safe_logic + '\n' + text[idx2:]
with codecs.open('app.py', 'w', 'utf-8') as f:
    f.write(new_text)

print("Injected fail-safe logic.")
