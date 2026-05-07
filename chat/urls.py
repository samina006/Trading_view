from django.urls import path
from chat.views import *

urlpatterns = [
    path('', home, name='home'),
    path('login/', login_page, name='login'),
    path('search/', search, name='search'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
]