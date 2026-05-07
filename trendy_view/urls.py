from django.urls import path
from django.contrib import admin
from chat import urls as chat_urls
from django.urls import include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(chat_urls)),
]