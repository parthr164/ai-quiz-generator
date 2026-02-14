from django.urls import path
from . import views

urlpatterns = [
    # path('', views.home, name='home')
    path("", views.upload_view, name="upload"),
    path("quiz/<str:quiz_id>/", views.quiz_view, name="quiz"),
    path("quiz/<str:quiz_id>/submit/", views.submit_view, name="submit"),
    path("quiz/<str:quiz_id>/download/", views.download_questions_view, name="download"),
]