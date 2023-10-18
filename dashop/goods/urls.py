from django.urls import path
from . import views

urlpatterns = [
    # 首页展示:v1/goods/index
    path("index", views.index_view),
]
