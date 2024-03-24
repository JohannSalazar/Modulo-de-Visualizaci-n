import json
from django.http import HttpResponse
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
import pandas as pd

@csrf_exempt
def obtener_datos_proyecto(request):
    # Obtener los datos del cuerpo de la solicitud
    data = json.loads(request.body.decode('utf-8'))
    nombre_campo = data.get('nombre_campo')
    cantidad_valores = data.get('cantidad_valores')
    fecha_inicio = data.get('fecha_inicio')
    fecha_fin = data.get('fecha_fin')
    proyecto_id = data.get('proyecto_id')
    nodo_id = data.get('nodo_id')  # Nuevo parámetro para el ID del nodo

    # Eliminar los microsegundos de las fechas de inicio y fin
    fecha_inicio = fecha_inicio.split('.')[0]
    fecha_fin = fecha_fin.split('.')[0]

    # Realizar la consulta SQL para obtener los datos
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT dv.id, dv.valor, dv.fecha_hora_lectura
            FROM dashboard_valor dv
            INNER JOIN dashboard_campo dc ON dv.campo_id = dc.id
            INNER JOIN dashboard_sensor ds ON dc.sensor_id = ds.id
            INNER JOIN dashboard_dispositivo dd ON ds.dispositivo_id = dd.id
            WHERE dc.nombre_de_campo = %s
            AND dv.fecha_hora_lectura BETWEEN %s AND %s
            AND dd.proyecto_id = %s
            AND dd.nodo_id = %s  -- Filtro por ID del nodo
            ORDER BY dv.fecha_hora_lectura DESC
        ''', [nombre_campo, fecha_inicio, fecha_fin, proyecto_id, nodo_id])
        rows = cursor.fetchall()

    # Convertir la estructura en una lista 
    rows = list(rows)

    # Procesar los resultados y convertirlos a formato DataFrame
    df = pd.DataFrame(rows, columns=['id', 'valor', 'fecha_lectura'])

    # Convertir la columna 'valor' a numérica y filtrar los valores no numéricos
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')  # Convertir a numérico
    df = df.dropna(subset=['valor'])  # Eliminar filas con valores no numéricos

    # Aplicar parametrizaciones específicas para 'temperatura' y 'humedad'
    if nombre_campo.lower() == 'temperatura':
        # Asegurarse de que los valores no sean menores a 0
        df = df[df['valor'] >= 0]
    elif nombre_campo.lower() == 'humedad':
        # Convertir los valores de humedad a porcentaje multiplicándolos por 0.10
        df['valor'] = round(df['valor'] * 0.10, 1)  # Limitar a un decimal

        # Asegurarse de que los valores de humedad no sean mayores a 100%
        df = df[df['valor'] <= 100]

    # Si hay menos datos válidos que la cantidad solicitada, recuperar más datos
    if len(df) < cantidad_valores:
        cantidad_faltante = cantidad_valores - len(df)
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT dv.id, dv.valor, dv.fecha_hora_lectura
                FROM dashboard_valor dv
                INNER JOIN dashboard_campo dc ON dv.campo_id = dc.id
                INNER JOIN dashboard_sensor ds ON dc.sensor_id = ds.id
                INNER JOIN dashboard_dispositivo dd ON ds.dispositivo_id = dd.id
                WHERE dc.nombre_de_campo = %s
                AND dv.fecha_hora_lectura BETWEEN %s AND %s
                AND dd.proyecto_id = %s
                AND dd.nodo_id = %s  -- Filtro por ID del nodo
                ORDER BY dv.fecha_hora_lectura DESC
                LIMIT %s
            ''', [nombre_campo, fecha_inicio, fecha_fin, proyecto_id, nodo_id, cantidad_faltante])
            additional_rows = cursor.fetchall()

        additional_df = pd.DataFrame(additional_rows, columns=['id', 'valor', 'fecha_lectura'])
        additional_df['valor'] = pd.to_numeric(additional_df['valor'], errors='coerce')  # Convertir a numérico
        additional_df = additional_df.dropna(subset=['valor'])  # Eliminar filas con valores no numéricos

        # Aplicar nuevamente los filtros de temperatura y humedad
        if nombre_campo.lower() == 'temperatura':
            additional_df = additional_df[additional_df['valor'] >= 0]
        elif nombre_campo.lower() == 'humedad':
            additional_df['valor'] = round(additional_df['valor'] * 0.10, 1)  # Limitar a un decimal
            additional_df = additional_df[additional_df['valor'] <= 100]

        # Concatenar los datos adicionales con el DataFrame original
        df = pd.concat([df, additional_df])

    # Ordenar por fecha_lectura y tomar la cantidad especificada de valores
    df = df.sort_values(by='fecha_lectura', ascending=False).head(cantidad_valores)

    # Preparar los datos de respuesta
    response_data = {
        "datos": df[['id', 'valor']].to_dict(orient='records'),
    }

    # Devolver los datos en formato JSON
    return HttpResponse(json.dumps(response_data), content_type='application/json')
