from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('submit/', views.submit_report, name='submit_report'),
    path('report/<int:report_id>/', views.report_detail, name='report_detail'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('ministry/login/', views.ministry_login_view, name='ministry_login'),
    path('ministry/logout/', views.ministry_logout_view, name='ministry_logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update_view, name='profile_update'),
    path('profile/<int:user_id>/', views.public_profile_view, name='public_profile'),
    path('dashboard/', views.ministry_dashboard, name='ministry_dashboard'),
    path('update-status/<int:report_id>/', views.update_status, name='update_status'),
    path('react/<int:report_id>/', views.add_reaction, name='add_reaction'),
]
