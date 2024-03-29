# En tu archivo urls.py de la aplicación VistaGrafica
from django.urls import path
from . import views

urlpatterns = [
    path('graficas/', views.graficas, name='graficas'),
    path('formHumedad/', views.formulario_humedad, name='formHumedad'),
    path('formTemperatura/', views.formulario_temperatura, name='formTemperatura'),# Definir tus URLs aquí
    # Otros patrones de URL aquí...
]
