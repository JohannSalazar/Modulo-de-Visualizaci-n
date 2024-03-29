from django.shortcuts import render
import plotly.graph_objects as go
import requests

def obtener_datos_proyecto(form_data):
    try:
        # Realizar la solicitud a la API con los datos del formulario
        response = requests.post("http://localhost:8000/api/consultardatos/", json=form_data)
        response.raise_for_status()  # Verificar si hubo errores en la solicitud
        data = response.json()
        return data
    except Exception as e:
        print("Error en la solicitud a la API:", e)
        return None
# views.py
def generar_grafica(data, tipo_grafica, color):
    if data and "datos" in data:
        valores_id = [item["id"] for item in data.get("datos", [])]
        valores_campo = [item["valor"] for item in data.get("datos", [])]

        # Determinar el tipo de gráfica y asignar el color correspondiente
        if tipo_grafica == "barras":
            fig = go.Figure(go.Bar(x=valores_id, y=valores_campo, marker_color=color))
        elif tipo_grafica == "dispersion":
            fig = go.Figure(go.Scatter(x=valores_id, y=valores_campo, mode='markers', marker_color=color))
        elif tipo_grafica == "lineal":
            fig = go.Figure(go.Scatter(x=valores_id, y=valores_campo, mode='lines', line_color=color))


        # Actualizar la configuración de la gráfica
        fig.update_layout(
            title=f'Gráfico de {tipo_grafica.capitalize()}',
            xaxis_title='ID',
            yaxis_title='Valor',
        )

        # Convertir la gráfica a HTML
        graph_html = fig.to_html(full_html=False)
        return graph_html
    else:
        return None




def graficas(request):
    if request.method == 'POST':
        # Si se envió un formulario POST, obtener los datos del formulario
        cantidad_valores = int(request.POST.get("cantidad_valores"))
        proyecto_id = int(request.POST.get("proyecto_id"))
        campo = request.POST.get("campo")
        fecha_inicio = request.POST.get("fecha_inicio")
        fecha_fin = request.POST.get("fecha_fin")
        hora_inicio = request.POST.get("hora_inicio")
        hora_fin = request.POST.get("hora_fin")
        tipo_grafica = request.POST.get("tipo_grafica")
        color = request.POST.get("color")
        

        # Construir el objeto form_data con los datos del formulario
        form_data = {
            "cantidad_valores": cantidad_valores,
            "proyecto_id": proyecto_id,
            "campo": campo,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
            "color": color
        }

        # Obtener los datos de la API con los datos del formulario
        data = obtener_datos_proyecto(form_data)

        # Generar la gráfica
        graph_html = generar_grafica(data, tipo_grafica, color)

        # Renderizar la plantilla con la gráfica incrustada
        return render(request, 'graficas.html', {'graph_html': graph_html})

    else:
        # Si la solicitud no es POST, renderizar la plantilla con el formulario vacío
        return render(request, 'graficas.html', {'graph_html': None})
    


def formulario_humedad(request):
    # Lógica para procesar el formulario de humedad
    return render(request, 'formHumedad.html')

def formulario_temperatura(request):
    # Lógica para procesar el formulario de temperatura
    return render(request, 'formTemperatura.html')
