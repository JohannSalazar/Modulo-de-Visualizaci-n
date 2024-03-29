import json
from django.http import HttpResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
from datetime import datetime

@csrf_exempt
def obtener_datos_proyecto(request):
    try:
        # Función para parsear diferentes formatos de fecha
        def parse_fecha(fecha):
            try:
                return datetime.strptime(fecha, '%Y-%m-%d')
            except ValueError:
                try:
                    return datetime.strptime(fecha, '%m-%d-%Y')
                except ValueError:
                    return datetime.strptime(fecha, '%d-%m-%Y')

        # Obtener los datos del cuerpo de la solicitud
        data = json.loads(request.body.decode('utf-8'))

        required_fields = ['cantidad_valores', 'proyecto_id', 'campo']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Falta el campo '{field}' en la solicitud")

        cantidad_valores = data['cantidad_valores']
        proyecto_id = data['proyecto_id']
        campo = data['campo']
        fecha_inicio = parse_fecha(data.get('fecha_inicio')) if data.get('fecha_inicio') else None
        fecha_fin = parse_fecha(data.get('fecha_fin')) if data.get('fecha_fin') else None
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')

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
            params.extend([fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')])
        if hora_inicio and hora_fin:
            sql_query += ' AND TIME(dv.fecha_hora_lectura) BETWEEN %s AND %s'
            params.extend([hora_inicio, hora_fin])

        with connection.cursor() as cursor:
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()

        if not rows:
            error_message = f"No hay datos disponibles para el campo '{campo}' entre {fecha_inicio} y {fecha_fin}"
            raise ValueError(error_message)

        df = pd.DataFrame(rows, columns=['id', 'valor', 'fecha_hora_lectura'])
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce')

        if campo.lower() == 'temperatura':
            df = df[(df['valor'] >= 0) & (df['valor'] <= 50)]  # Filtrar valores válidos de temperatura
        elif campo.lower() == 'humedad':
            df['valor'] = df['valor'] * 0.10  # Convertir a porcentaje
            df = df[(df['valor'] >= 0) & (df['valor'] <= 100)]  # Filtrar valores válidos de humedad

        df = df.head(cantidad_valores)
        df['fecha'] = df['fecha_hora_lectura'].dt.strftime('%Y-%m-%d')

        if hora_inicio and hora_fin:
            df['hora'] = df['fecha_hora_lectura'].dt.strftime('%H:%M:%S')

        del df['fecha_hora_lectura']

        response_data = {
            "datos": []
        }

        for index, row in df.iterrows():
            valor = round(row['valor'], 2)  # Redondear a dos dígitos después del punto decimal
            data_row = {
                "id": row['id'],
                "grados" if campo.lower() == 'temperatura' else "porcentaje": valor
            }
            if fecha_inicio and fecha_fin:
                data_row["fecha"] = row['fecha']
            if hora_inicio and hora_fin:
                data_row["hora"] = row['hora']
            response_data['datos'].append(data_row)

        # Calcular métricas
        metrics_df = df['valor']
        metrics = {
            "media": round(metrics_df.mean(), 2),
            "mediana": round(metrics_df.median(), 2),
            "frecuencia": int(metrics_df.value_counts().max()),
            "moda": round(metrics_df.mode()[0], 2)
        }

        response_data.update(metrics)

        return HttpResponse(json.dumps(response_data), content_type='application/json')

    except ValueError as ve:
        response_data = {'error': str(ve)}
        return HttpResponse(json.dumps(response_data), content_type='application/json', status=400)

    except Exception as e:
        response_data = {'error': 'Ocurrió un error interno en el servidor'}
        return HttpResponse(json.dumps(response_data), content_type='application/json', status=500)

