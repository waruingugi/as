from django.urls import path

from users.views.users import (
    AppSubscribersView,
    SignalSettingViewSet,
    UserCreateView,
    UserListView,
    UserRetrieveUpdateView,
)

app_name = "users"

urlpatterns = [
    # Signal Settings
    path(
        "signal-settings/",
        SignalSettingViewSet.as_view({"get": "list", "post": "create"}),
        name="signal-settings",
    ),
    path(
        "signal-settings/<str:id>/",
        SignalSettingViewSet.as_view({"get": "retrieve"}),
        name="signal-settings-detail",
    ),
    # App Subscribers
    path(
        "app-subscribers/<str:app>/",
        AppSubscribersView.as_view(),
        name="app-subscribers",
    ),
    # User Management
    path("create/", UserCreateView.as_view(), name="create"),
    path("", UserListView.as_view(), name="list"),
    path("<str:id>/", UserRetrieveUpdateView.as_view(), name="detail"),
]
