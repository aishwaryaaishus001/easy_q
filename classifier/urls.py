from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('generate_question_paper/', views.generate_question_paper, name='generate-question-paper'),
    path('history/', views.history, name='view-history'),
    path('teacher/login/', views.teacher_login, name='teacher-login'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher-dashboard'),
    path('teacher/logout/', views.teacher_logout, name='teacher-logout'),
    path('teacher/generate/', views.generate_question_paper, name='create-question-paper'),
    path('teacher/add/', views.add_question, name='add-question'),
    path('teacher/add/predict_difficulty/', views.predict_difficulty_view, name='predict-difficulty')
    #path('history/', views.view_history, name='view-history'),
]
