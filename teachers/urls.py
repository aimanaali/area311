from django.urls import path

from . import views

app_name = 'teachers'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('courses/new/', views.create_course, name='create_course'),
    path('courses/<int:course_id>/', views.manage_course, name='manage_course'),
    path('courses/<int:course_id>/enrollments/new/', views.enroll_student, name='enroll_student_in_course'),
    path('courses/<int:course_id>/live-classes/new/', views.create_live_class, name='schedule_course_live_class'),
    path('lessons/new/', views.create_lesson, name='create_lesson'),
    path('live-classes/new/', views.create_live_class, name='create_live_class'),
    path('live-classes/<int:live_class_id>/edit/', views.create_live_class, name='edit_live_class'),
    path('live-classes/<int:live_class_id>/cancel/', views.cancel_live_class, name='cancel_live_class'),
    path('assignments/new/', views.create_assignment, name='create_assignment'),
    path('enrollments/new/', views.enroll_student, name='enroll_student'),
    path('submissions/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),
]
