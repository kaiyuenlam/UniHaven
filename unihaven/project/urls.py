# project-level urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # All API endpoints will be available under '/api/'.
    path('api/', include('core.urls')),
]
