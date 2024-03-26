import json
from django.http import HttpResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
import pandas as pd

@csrf_exempt
def obtener_datos_proyecto(request):
    try:
        # Obtener los datos del cuerpo de la solicitud
        data = json.loads(request.body.decode('utf-8'))
        # Imprimir los datos recibidos para depuración
        print("Datos recibidos:", data)

        # Validar que todos los campos necesarios estén presentes y tengan valores válidos
        required_fields = ['cantidad_valores', 'proyecto_id', 'campo', 'fecha_inicio', 'fecha_fin']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Falta el campo '{field}' en la solicitud")

        # Obtener los valores de los campos
        cantidad_valores = data['cantidad_valores']
        proyecto_id = data['proyecto_id']
        campo = data['campo']
        fecha_inicio = data['fecha_inicio']
        fecha_fin = data['fecha_fin']
        hora_inicio = data.get('hora_inicio')  # Obtener la hora de inicio si está presente, o None si no lo está
        hora_fin = data.get('hora_fin')  # Obtener la hora de fin si está presente, o None si no lo está

        # Construir la consulta SQL base
        sql_query = '''
            SELECT dv.id, dv.valor, dv.fecha_hora_lectura
            FROM dashboard_valor dv
            INNER JOIN dashboard_campo dc ON dv.campo_id = dc.id
            INNER JOIN dashboard_sensor ds ON dc.sensor_id = ds.id
            INNER JOIN dashboard_dispositivo dd ON ds.dispositivo_id = dd.id
            WHERE dc.nombre_de_campo = %s
            AND dd.proyecto_id = %s
        '''

        # Agregar condiciones de filtrado para el campo y el rango de fechas si están presentes
        params = [campo, proyecto_id]
        if fecha_inicio and fecha_fin:
            sql_query += ' AND DATE(dv.fecha_hora_lectura) BETWEEN %s AND %s'
            params.extend([fecha_inicio, fecha_fin])
        if hora_inicio is not None and hora_fin is not None:
            sql_query += ' AND TIME(dv.fecha_hora_lectura) BETWEEN %s AND %s'
            params.extend([hora_inicio, hora_fin])

        # Realizar la consulta SQL para obtener los datos
        with connection.cursor() as cursor:
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()

        # Verificar si se devolvieron datos vacíos
        if not rows:
            # Construir un mensaje de error más descriptivo
            error_message = f"No hay datos disponibles para el campo '{campo}' entre {fecha_inicio} y {fecha_fin}"
            raise ValueError(error_message)

        # Convertir la estructura en un DataFrame
        df = pd.DataFrame(rows, columns=['id', 'valor', 'fecha_hora_lectura'])

        # Convertir el campo 'valor' a numérico
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce')

        # Filtrar valores negativos para temperatura
        if campo.lower() == 'temperatura':
            df = df[df['valor'] >= 0]  # Filtrar valores negativos
            df['valor'] = df['valor'].round(2)  # Redondear a dos decimales
        elif campo.lower() == 'humedad':
            df['valor'] = df['valor'] * 0.10  # Convertir a porcentaje
            df['valor'] = df['valor'].round(2)  # Redondear a dos decimales
            df = df[df['valor'] <= 100]  # Filtrar valores de humedad mayores a 100

        # Tomar la cantidad especificada de valores
        df = df.head(cantidad_valores)

        # Preparar los datos de respuesta
        response_data = {
            "datos": df[['id', 'valor']].to_dict(orient='records'),
        }

        # Devolver los datos en formato JSON
        return HttpResponse(json.dumps(response_data), content_type='application/json')

    except ValueError as ve:
        # Error en la solicitud o datos no disponibles
        response_data = {'error': str(ve)}
        return HttpResponse(json.dumps(response_data), content_type='application/json', status=400)

    except Exception as e:
        # Error interno del servidor
        response_data = {'error': 'Ocurrió un error interno en el servidor'}
        return HttpResponse(json.dumps(response_data), content_type='application/json', status=500)
