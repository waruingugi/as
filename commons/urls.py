from django.urls import path

from commons.views import AppVersionView

urlpatterns = [
    path("commons/app-version/", AppVersionView.as_view(), name="app-version"),
]
