from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_listing, name='create_listing'),
    path('dashboard/', views.donor_dashboard, name='donor_dashboard'),
    path('dashboard/claimant/', views.claimant_dashboard, name='claimant_dashboard'),
    path('claim/<int:listing_id>/', views.claim_listing, name='claim_listing'),
    path('claim/approve/<int:claim_id>/', views.approve_claim, name='approve_claim'),
    path('claim/reject/<int:claim_id>/', views.reject_claim, name='reject_claim'),
    path('claim/complete/<int:claim_id>/', views.complete_claim, name='complete_claim'),
    path('assign-volunteer/<int:claim_id>/', views.assign_volunteer, name='assign_volunteer'),
    path('api/', views.listing_api, name='listing_api'),
    path('my-claims/', views.my_claims, name='my_claims'),
    path('history/', views.history_view, name='history'),
]
