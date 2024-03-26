from django.urls import path
from API import views

urlpatterns = [
    path('consultardatos/', views.obtener_datos_proyecto, name='consultar_datos'),
]