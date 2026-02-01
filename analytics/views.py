from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from listings.models import Listing, Claim
from django.contrib.auth import get_user_model

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('dashboard')

    # Impact Metrics
    completed_claims = Claim.objects.filter(status='completed')
    total_kg = completed_claims.aggregate(Sum('listing__quantity_kg'))['listing__quantity_kg__sum'] or 0
    
    meals_served = int(total_kg * 3)
    co2_saved = round(total_kg * 3.5, 2)
    
    # Recent activity
    recent_claims = Claim.objects.all().order_by('-claimed_at')[:10]
    
    # Users for leaderboard table in dashboard
    User = get_user_model()
    users_list = User.objects.all().order_by('-trust_score')[:5]

    return render(request, 'analytics/dashboard.html', {
        'total_kg': total_kg,
        'meals_served': meals_served,
        'co2_saved': co2_saved,
        'recent_claims': recent_claims,
        'users_list': users_list
    })



def leaderboard_view(request):
    User = get_user_model()
    
    # Aggregate data for all donors
    # In a real app, this should be efficiently cached or pre-calculated
    donors = User.objects.filter(role='donor').annotate(
        total_donated_kg=Sum('listings__quantity_kg', default=0)
    ).order_by('-total_donated_kg')[:10]
    
    # Global Stats
    completed_claims = Claim.objects.filter(status='completed')
    total_kg = completed_claims.aggregate(Sum('listing__quantity_kg'))['listing__quantity_kg__sum'] or 0
    meals_served = int(total_kg * 3)
    active_donors = User.objects.filter(role='donor').count()

    return render(request, 'analytics/leaderboard.html', {
        'donors': donors,
        'total_kg': total_kg,
        'meals_served': meals_served,
        'active_donors': active_donors
    })

from django.http import JsonResponse
from foodsaver.ai_core import get_surplus_prediction

def predict_surplus(request):
    data = get_surplus_prediction()
    return JsonResponse({'message': data['prediction']})
