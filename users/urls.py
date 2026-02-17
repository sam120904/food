from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('directory/', views.ngo_directory, name='ngo_directory'),
    path('profile/<int:user_id>/', views.profile_view, name='profile_view'),
    path('connected-ngos/', views.connected_ngos, name='connected_ngos'),
    path('add-volunteer/', views.add_volunteer, name='add_volunteer'),
    # Volunteer portal
    path('volunteer/login/', views.volunteer_login, name='volunteer_login'),
    path('volunteer/dashboard/', views.volunteer_dashboard, name='volunteer_dashboard'),
    path('volunteer/toggle-status/', views.toggle_volunteer_status, name='toggle_volunteer_status'),
    path('volunteer/pickup/<int:assignment_id>/update/', views.update_pickup_status, name='update_pickup_status'),
]
