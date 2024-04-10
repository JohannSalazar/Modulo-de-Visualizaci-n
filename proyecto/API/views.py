import json
from django.http import HttpResponse
from django.db import connection
import pandas as pd
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt

# Paso 1: Definición de funciones auxiliares

def parse_fecha(fecha):
    if not fecha:
        return None
    
    formatos_de_fecha = ['%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y']
    for formato in formatos_de_fecha:
        try:
            return datetime.strptime(fecha, formato).date()
        except ValueError:
            continue
    
    raise ValueError("Formato de fecha no válido")

def obtener_datos_de_base_de_datos(campo, proyecto_id, cantidad_valores, fecha_inicio=None, fecha_fin=None, hora_inicio=None, hora_fin=None):
    sql_query = '''
        SELECT dv.id, dv.valor, dv.fecha_hora_lectura
        FROM dashboard_valor dv
        INNER JOIN dashboard_campo dc ON dv.campo_id = dc.id
        INNER JOIN dashboard_sensor ds ON dc.sensor_id = ds.id
        INNER JOIN dashboard_dispositivo dd ON ds.dispositivo_id = dd.id
        WHERE dc.nombre_de_campo = %s
        AND dd.proyecto_id = %s
    '''
    
    params = [campo, proyecto_id]

    if fecha_inicio and fecha_fin:
        sql_query += ' AND DATE(dv.fecha_hora_lectura) BETWEEN %s AND %s'
        params.extend([fecha_inicio, fecha_fin])
    if hora_inicio and hora_fin:
        sql_query += ' AND TIME(dv.fecha_hora_lectura) BETWEEN %s AND %s'
        params.extend([hora_inicio, hora_fin])

    sql_query += ' ORDER BY dv.id ASC LIMIT %s'
    params.append(cantidad_valores)

    with connection.cursor() as cursor:
        cursor.execute(sql_query, params)
        rows = cursor.fetchall()

    return rows

# Paso 2: Definición de funciones principales

def limpiar_datos(df, campo):
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')

    if campo.lower() == 'temperatura':
        df_filtrado = df[(df['valor'] >= 0) & (df['valor'] <= 50)]
        datos_atipicos = df[(df['valor'] < 0) | (df['valor'] > 50)]
    elif campo.lower() == 'humedad':
        df['valor'] = (df['valor'] * 0.10).round(1)
        df_filtrado = df[(df['valor'] >= 0) & (df['valor'] <= 100)]
        datos_atipicos = df[(df['valor'] < 0) | (df['valor'] > 100)]
    else:
        df_filtrado = df
        datos_atipicos = pd.DataFrame(columns=['id', 'valor', 'fecha_hora_lectura'])

    return df_filtrado, datos_atipicos

def calcular_estadisticas(df_filtrado):
    media = df_filtrado['valor'].mean()
    mediana = df_filtrado['valor'].median()
    moda = df_filtrado['valor'].mode()
    frecuencia = df_filtrado['valor'].value_counts().idxmax()
    return media, mediana, moda, frecuencia

def obtener_datos_y_estadisticas(campo, proyecto_id, cantidad_valores, fecha_inicio=None, fecha_fin=None, hora_inicio=None, hora_fin=None, datos_base_de_datos=None):
    try:
        df = pd.DataFrame(datos_base_de_datos, columns=['id', 'valor', 'fecha_hora_lectura'])

        df_filtrado, datos_atipicos = limpiar_datos(df, campo)

        response_data = {
            "datos_buenos": [],
            "datos_atipicos": [],
            "mensaje": f"{len(datos_atipicos)} valores atípicos encontrados para el campo '{campo}'"
        }

        for index, row in df_filtrado.iterrows():
            valor = round(row['valor'], 2)
            estado = ""
            if campo.lower() == 'temperatura':
                if valor <= 10:
                    estado = "rojo"
                elif valor <= 19:
                    estado = "amarillo"
                else:
                    estado = "verde"
            elif campo.lower() == 'humedad':
                if valor <= 25:
                    estado = "seco"
                elif valor <= 50:
                    estado = "húmedo"
                elif valor <= 80:
                    estado = "muy húmedo"
                elif valor <= 95:
                    estado = "altamente saturado"
                else:
                    estado = "saturado"

            data_row = {
                "id": row['id'],
                "grados" if campo.lower() == 'temperatura' else "porcentaje": valor,
                "estado": estado,
                "fecha": row['fecha_hora_lectura'].strftime('%Y-%m-%d'),
                "hora": row['fecha_hora_lectura'].strftime('%H:%M:%S')
            }
            response_data['datos_buenos'].append(data_row)

        for index, row in datos_atipicos.iterrows():
            valor = round(row['valor'], 2)
            data_row = {
                "id": row['id'],
                "grados" if campo.lower() == 'temperatura' else "porcentaje": valor,
                "fecha": row['fecha_hora_lectura'].strftime('%Y-%m-%d'),
                "hora": row['fecha_hora_lectura'].strftime('%H:%M:%S')
            }
            response_data['datos_atipicos'].append(data_row)
        
        if not df_filtrado.empty:
            media, mediana, moda, frecuencia = calcular_estadisticas(df_filtrado)
            response_data.update({
                "media": round(media, 2),
                "mediana": round(mediana, 2),
                "moda": round(float(moda.iloc[0]), 2),
                "frecuencia": int(frecuencia)
            })

        return response_data

    except ValueError as ve:
        return {'error': str(ve)}
    except Exception as e:
        return {'error': 'Ocurrió un error interno en el servidor'}

@csrf_exempt
def obtener_datos_proyecto(request):
    try:
        data = json.loads(request.body.decode('utf-8'))

        required_fields = ['cantidad_valores', 'proyecto_id', 'campo']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Falta el campo '{field}' en la solicitud")

        cantidad_valores = data['cantidad_valores']
        proyecto_id = data['proyecto_id']
        campo = data['campo']
        fecha_inicio = parse_fecha(data.get('fecha_inicio', ''))
        fecha_fin = parse_fecha(data.get('fecha_fin', ''))
        hora_inicio = data.get('hora_inicio', '')
        hora_fin = data.get('hora_fin', '')

        datos_base_de_datos = obtener_datos_de_base_de_datos(campo, proyecto_id, cantidad_valores, fecha_inicio, fecha_fin, hora_inicio, hora_fin)

        response_data = obtener_datos_y_estadisticas(campo, proyecto_id, cantidad_valores, fecha_inicio, fecha_fin, hora_inicio, hora_fin, datos_base_de_datos)

        return HttpResponse(json.dumps(response_data), content_type='application/json')

    except ValueError as ve:
        if "cannot convert float" in str(ve):
            response_data = {'error': 'Ocurrió un error en el servidor'}
            return HttpResponse(json.dumps(response_data), content_type='application/json', status=500)
        else:
            response_data = {'error': str(ve)}
            return HttpResponse(json.dumps(response_data), content_type='application/json', status=400)

    except Exception as e:
        response_data = {'error': 'Ocurrió un error en el servidor'}
        return HttpResponse(json.dumps(response_data), content_type='application/json', status=500)
