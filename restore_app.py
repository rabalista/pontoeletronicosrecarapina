import codecs

safe_logic = """def get_admin_report_excel(curr_user_mat, role):
    if role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 401
    target_user_id = request.args.get('user_id')
    fmt = request.args.get('format', 'excel') # excel or json
    
    conn = get_db_connection()
    ph = get_ph(conn)
    try:

        cursor = conn.cursor()
        query = \"\"\"
            SELECT t.matricula, t.user_name AS name,
                   t.record_type, t.timestamp, t.neighborhood, t.city,
                   t.latitude, t.longitude, t.accuracy, t.full_address,
                   t.is_retroactive, t.justification, t.document_path, t.is_reviewed
            FROM TimeRecords t
        \"\"\"
        params = []
        if target_user_id:
            query += f" WHERE t.user_id = {ph}"
            params.append(target_user_id)
        query += " ORDER BY t.timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()

        if fmt == 'json':
             # Return raw data for frontend PDF generation
             records = []
             for r in rows:
                 ts = rf(r, 'timestamp')
                 if isinstance(ts, datetime.datetime):
                     ts = ts.strftime('%Y-%m-%d %H:%M:%S')
                 else:
                     ts = str(ts)
                 
                 records.append({
                     'matricula': rf(r, 'matricula'),
                     'name': rf(r, 'name'),
                     'type': rf(r, 'record_type'),
                     'timestamp': ts,
                     'neighborhood': rf(r, 'neighborhood'),
                     'city': rf(r, 'city'),
                     'full_address': rf(r, 'full_address'),
                     'is_retroactive': bool(rf(r, 'is_retroactive')),
                     'justification': rf(r, 'justification'),
                     'document_path': rf(r, 'document_path')
                 })
             return jsonify(records)
        
        # Build Cargo and Workload Map
        cargo_map = {}
        workload_map = {}
        try:
            c_conn = get_db_connection()
            c_cur = c_conn.cursor()
            nolock = "" if isinstance(c_conn, sqlite3.Connection) else "WITH (NOLOCK)"
            c_cur.execute(f"SELECT matricula, cargo, workload FROM Users {nolock}")
            for cr in c_cur.fetchall():
                mat = rf(cr, 'matricula')
                cargo_map[mat] = rf(cr, 'cargo')
                workload_map[mat] = rf(cr, 'workload')
            c_conn.close()
        except: pass

        wb = openpyxl.Workbook()
        if target_user_id:
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
                raise e_main
        else:
            wb.remove(wb.active)
            groups = {}
            for r in rows:
                k = (rf(r,'matricula'), rf(r,'name'))
                groups.setdefault(k, []).append(r)
            for (m, n), items in groups.items():
                ws = wb.create_sheet(title=(n or m or "User")[:30])
                ws.append(["Matricula", "Nome", "Cargo", "Tipo", "Data/Hora", "Bairro", "Cidade", "Latitude", "Longitude", "Precisão (m)", "Endereço Completo", "Manual?", "Justificativa", "Anexo"])
                for r in items:
                    mat = rf(r,'matricula')
                    c = cargo_map.get(mat, 'Funcionario')
                    ws.append([mat, rf(r,'name'), c, rf(r,'record_type'), rf(r,'timestamp'), rf(r,'neighborhood'), rf(r,'city'), rf(r,'latitude'), rf(r,'longitude'), rf(r,'accuracy'), rf(r,'full_address'), 'Sim' if rf(r,'is_retroactive') else 'Não', rf(r,'justification') or '', rf(r,'document_path') or ''])
        
        out = BytesIO()
        wb.save(out)
        out.seek(0)
        return send_file(out, download_name="relatorio_admin.xlsx", as_attachment=True)
    except Exception as e:
        print(f"Excel Error: {e}")
        return jsonify({'message': str(e)}), 500
    finally:
        try: conn.close()
        except: pass"""

with codecs.open('app.py', 'r', 'utf-8') as f:
    text = f.read()

s_idx = text.find("def get_admin_report_excel(curr_user_mat, role):")
e_idx = text.find("        except: pass", s_idx) + 20

new_text = text[:s_idx] + safe_logic + text[e_idx:]
with codecs.open('app.py', 'w', 'utf-8') as f:
    f.write(new_text)

print("Restored entire function properly.")
