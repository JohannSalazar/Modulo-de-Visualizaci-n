from django.conf.urls import url
from API import views

urlpatterns = [
    url(r'^consultar_datos/$', views.obtener_datos_proyecto, name='consultar_datos'),
]

urlpatterns = [
    url(r'^consultar_datos/$', views.obtener_datos_proyecto, name='consultar_datos'),
]
