from django.urls import path

from observers.views.multipliers import MultiplierCreateView, MultiplierListView

app_Name = "multipliers"

urlpatterns = [
    path("create/", MultiplierCreateView.as_view(), name="create"),
    path("", MultiplierListView.as_view(), name="list"),
]
