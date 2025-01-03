from django.urls import path

from users.views.users import UserCreateView, UserListView, UserRetrieveUpdateView

app_name = "users"

urlpatterns = [
    path("create/", UserCreateView.as_view(), name="create"),
    path("", UserListView.as_view(), name="list"),
    path("<str:id>/", UserRetrieveUpdateView.as_view(), name="detail"),
]
