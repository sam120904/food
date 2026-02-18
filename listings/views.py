from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Listing, Claim, PickupAssignment
from .forms import ListingForm

@login_required
def create_listing(request):
    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.donor = request.user
            listing.save()
            return redirect('donor_dashboard')
    else:
        form = ListingForm()
    return render(request, 'listings/create_listing.html', {'form': form})

@login_required
def donor_dashboard(request):
    if request.user.role != 'donor' and not request.user.is_superuser:
         return redirect('dashboard')
         
    # Auto-expire listings past their expiry time
    Listing.objects.filter(
        status='active',
        expiry_time__lte=timezone.now()
    ).update(status='expired')

    listings = Listing.objects.filter(donor=request.user).order_by('-created_at')
    
    # Split claims into Pending and History
    pending_claims = Claim.objects.filter(listing__in=listings, status='pending').order_by('-claimed_at')
    # History includes completed, rejected, and approved (if any legacy exist)
    history_claims = Claim.objects.filter(listing__in=listings, status__in=['completed', 'rejected', 'approved']).order_by('-claimed_at')
    
    # Get pickup assignments for this restaurant's listings (with OTPs)
    active_pickups_qs = PickupAssignment.objects.filter(
        claim__listing__in=listings,
        status__in=['assigned', 'picked_up'],
    ).select_related(
        'claim', 'claim__listing', 'claim__claimant', 'volunteer', 'otp'
    ).order_by('-assigned_at')

    # Pre-process pickups so template only needs short, simple variables
    pickup_list = []
    for p in active_pickups_qs:
        otp_obj = getattr(p, 'otp', None)
        pickup_list.append({
            'id': p.id,
            'ftype': p.claim.listing.food_type,
            'desc': p.claim.listing.description,
            'qty': p.claim.listing.quantity_kg,
            'vname': p.volunteer.name,
            'ngo': getattr(p.claim.claimant, 'institution_name', '') or p.claim.claimant.username,
            'assigntime': p.assigned_at,
            'pstatus': p.status,
            'otp_code': otp_obj.code if otp_obj else '',
            'otp_verified': otp_obj.is_verified if otp_obj else False,
            'otp_verified_at': otp_obj.verified_at if otp_obj else None,
        })

    return render(request, 'listings/donor_dashboard.html', {
        'listings': listings, 
        'pending_claims': pending_claims,
        'history_claims': history_claims,
        'pickup_list': pickup_list,
        'pickup_count': len(pickup_list),
    })

@login_required
def claim_listing(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    if request.method == 'POST':
        # Create claim with default status 'pending'
        Claim.objects.create(listing=listing, claimant=request.user)
        return redirect('claimant_dashboard')
    return render(request, 'listings/claim_confirm.html', {'listing': listing})

@login_required
def approve_claim(request, claim_id):
    # Approve the claim — NGO will then assign a volunteer for pickup
    claim = get_object_or_404(Claim, id=claim_id)
    if request.user == claim.listing.donor:
        claim.status = 'approved'
        claim.save()
        
        # Mark listing as claimed (not completed until delivered)
        listing = claim.listing
        listing.status = 'claimed'
        listing.save()
        
    return redirect('donor_dashboard')

@login_required
def reject_claim(request, claim_id):
    claim = get_object_or_404(Claim, id=claim_id)
    if request.user == claim.listing.donor:
        claim.status = 'rejected'
        claim.save()
        # Listing remains active for others to claim
    return redirect('donor_dashboard')

# Legacy verify view can be removed or redirected if no longer used
@login_required
def complete_claim(request, claim_id):
    return approve_claim(request, claim_id)

@login_required
def claimant_dashboard(request):
    if request.user.role != 'claimant' and not request.user.is_superuser:
        return redirect('dashboard')
    
    # Get volunteers for this NGO
    from users.models import Volunteer
    volunteers = Volunteer.objects.filter(ngo=request.user).order_by('-date_joined')
    active_volunteers_list = volunteers.filter(status='active')
    active_volunteers = active_volunteers_list.count()
    total_volunteers = volunteers.count()

    # Pre-process volunteers for template (short variable names)
    vol_list = []
    for v in volunteers:
        vol_list.append({
            'vid': v.volunteer_id,
            'name': v.name,
            'initial': v.name[:1].upper() if v.name else '?',
            'phone': v.phone or '\u2014',
            'email': v.email or '\u2014',
            'addr': v.address or '\u2014',
            'status': v.status,
            'joined': v.date_joined,
            'id': v.id,
        })
    
    # Auto-expire listings that have passed their expiry time
    Listing.objects.filter(
        status='active',
        expiry_time__lte=timezone.now()
    ).update(status='expired')

    # Get active (non-expired) listings for list view
    listings = Listing.objects.filter(
        status='active',
        expiry_time__gt=timezone.now()
    ).order_by('expiry_time')
    
    # Get IDs of listings this user has already claimed (pending)
    my_pending_claims_ids = Claim.objects.filter(
        claimant=request.user, 
        status='pending'
    ).values_list('listing_id', flat=True)

    # --- Claims Management ---
    
    # 1. Pending Approval (Waitlist)
    pending_claims = Claim.objects.filter(
        claimant=request.user, 
        status='pending'
    ).select_related('listing', 'listing__donor').order_by('-claimed_at')

    # Pre-process pending claims for template (short variable names)
    pending_list = []
    for c in pending_claims:
        pending_list.append({
            'id': c.id,
            'desc': c.listing.description,
        })
    
    # 2. Approved Claims (Need assignment)
    # Get all approved claims first
    approved_claims_qs = Claim.objects.filter(
        claimant=request.user,
        status='approved'
    ).select_related('listing', 'listing__donor').order_by('-claimed_at')
    
    # Identify which approved claims already have an assignment
    assigned_claim_ids = PickupAssignment.objects.filter(
        claim__in=approved_claims_qs
    ).values_list('claim_id', flat=True)
    
    # Filter: Unassigned (Action Required)
    unassigned_claims = approved_claims_qs.exclude(id__in=assigned_claim_ids)
    
    # Filter: Assigned (In Progress)
    assigned_pickup_tasks_qs = PickupAssignment.objects.filter(
        claim__in=approved_claims_qs
    ).select_related('claim', 'volunteer', 'claim__listing', 'claim__listing__donor').order_by('-assigned_at')

    # Pre-process unassigned claims for template (short variable names)
    unassigned_list = []
    for c in unassigned_claims:
        donor = c.listing.donor
        unassigned_list.append({
            'id': c.id,
            'desc': c.listing.description,
            'donor_name': getattr(donor, 'institution_name', '') or donor.username,
            'qty': c.listing.quantity_kg,
        })

    # Pre-process assigned pickup tasks for template
    assigned_tasks_list = []
    for t in assigned_pickup_tasks_qs:
        assigned_tasks_list.append({
            'id': t.id,
            'desc': t.claim.listing.description,
            'vname': t.volunteer.name,
            'assigntime': t.assigned_at,
            'status_display': t.get_status_display(),
        })

    return render(request, 'listings/claimant_dashboard.html', {
        'listings': listings, 
        'pending_claim_ids': my_pending_claims_ids,
        
        # Volunteer Data
        'volunteers': volunteers,
        'vol_list': vol_list,
        'active_volunteers': active_volunteers,
        'active_volunteers_list': active_volunteers_list,
        'total_volunteers': total_volunteers,
        
        # Claims Data
        'pending_claims': pending_claims,
        'pending_list': pending_list,
        'unassigned_claims': unassigned_claims,
        'unassigned_list': unassigned_list,
        'assigned_pickup_tasks': assigned_pickup_tasks_qs,
        'assigned_tasks_list': assigned_tasks_list,
    })


@login_required
def assign_volunteer(request, claim_id):
    """NGO assigns an active volunteer to pick up an approved claim."""
    if request.user.role != 'claimant' or request.method != 'POST':
        return redirect('dashboard')
    
    from users.models import Volunteer
    claim = get_object_or_404(Claim, id=claim_id, claimant=request.user, status='approved')
    volunteer_id = request.POST.get('volunteer_id')
    volunteer = get_object_or_404(Volunteer, id=volunteer_id, ngo=request.user, status='active')
    
    # Create pickup assignment
    PickupAssignment.objects.create(
        claim=claim,
        volunteer=volunteer,
        notes=request.POST.get('notes', '')
    )
    
    return redirect('claimant_dashboard')

from django.http import JsonResponse

def listing_api(request):
    listings = Listing.objects.filter(status='active')
    data = []
    for listing in listings:
        data.append({
            'id': listing.id,
            'food_type': listing.get_food_type_display(),
            'quantity': listing.quantity_kg,
            'lat': listing.donor.latitude if listing.donor.latitude else 0,
            'lng': listing.donor.longitude if listing.donor.longitude else 0,
            'expiry': listing.expiry_time.isoformat(),
            'donor_name': listing.donor.username,
        })
    return JsonResponse({'listings': data})

@login_required
def my_claims(request):
    if request.user.role != 'claimant':
        return redirect('dashboard')
    
    # Active claims (pending or approved)
    claims = Claim.objects.filter(claimant=request.user, status__in=['pending', 'approved']).order_by('-claimed_at')
    return render(request, 'listings/my_claims.html', {'claims': claims})

@login_required
def history_view(request):
    if request.user.role != 'claimant':
        return redirect('dashboard')
        
    # Past claims (completed or rejected)
    claims = Claim.objects.filter(claimant=request.user, status__in=['completed', 'rejected']).order_by('-claimed_at')
    return render(request, 'listings/history.html', {'claims': claims})

