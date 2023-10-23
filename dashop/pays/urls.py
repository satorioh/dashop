from django.urls import path
from . import views

urlpatterns = [
    # ReturnURL: v1/pays/return_url
    path("return_url", views.ReturnUrlView.as_view()),
]
