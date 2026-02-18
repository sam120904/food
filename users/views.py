import secrets
import string

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from .forms import CustomUserCreationForm
from .models import User, Volunteer


def _generate_password(length=10):
    """Generate a random password for volunteer accounts."""
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(length))


def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect based on role
            if user.role == 'donor':
                return redirect('donor_dashboard')
            elif user.role == 'claimant':
                return redirect('claimant_dashboard')
            elif user.role == 'volunteer':
                return redirect('volunteer_dashboard')
            elif user.role == 'admin':
                return redirect('/admin/')
            else:
                return redirect('index')
        else:
            return render(request, 'users/login.html', {
                'error': 'Invalid username or password.'
            })
    return render(request, 'users/login.html')


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def dashboard(request):
    if request.user.role == 'donor':
        return redirect('donor_dashboard')
    elif request.user.role == 'claimant':
        return redirect('claimant_dashboard')
    elif request.user.role == 'volunteer':
        return redirect('volunteer_dashboard')
    elif request.user.role == 'admin':
        return redirect('/admin/')
    return render(request, 'users/dashboard_placeholder.html', {'role': 'Unknown'})


@login_required
def add_volunteer(request):
    if request.user.role != 'claimant':
        return redirect('dashboard')
    if request.method == 'POST':
        from .forms import VolunteerForm
        form = VolunteerForm(request.POST)
        if form.is_valid():
            volunteer = form.save(commit=False)
            volunteer.ngo = request.user

            # Create a user account for the volunteer
            email = form.cleaned_data.get('email', '')
            name = form.cleaned_data.get('name', 'volunteer')

            # Generate username from name + random suffix
            base_username = name.lower().replace(' ', '_')[:15]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            # Generate random password
            raw_password = _generate_password()

            # Create user with volunteer role
            vol_user = User.objects.create_user(
                username=username,
                email=email,
                password=raw_password,
                role='volunteer',
                institution_name=request.user.institution_name,
            )

            volunteer.user = vol_user
            volunteer.save()

            # Send email with credentials
            if email:
                ngo_name = request.user.institution_name or request.user.username
                subject = f"Welcome to Food Saver — You've been invited by {ngo_name}"
                message = (
                    f"Hello {name},\n\n"
                    f"You have been added as a volunteer by {ngo_name} on Food Saver.\n\n"
                    f"Here are your login credentials:\n"
                    f"  Portal: http://localhost:8000/users/volunteer/login/\n"
                    f"  Username: {username}\n"
                    f"  Password: {raw_password}\n\n"
                    f"Your Volunteer ID: {volunteer.volunteer_id}\n\n"
                    f"Please log in and change your password at your earliest convenience.\n\n"
                    f"Together, let's end hunger!\n"
                    f"— Food Saver Team"
                )
                try:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send volunteer invitation email to {email}: {e}")

    return redirect('claimant_dashboard')


# ======== VOLUNTEER PORTAL VIEWS ========

def volunteer_login(request):
    """Dedicated login page for volunteers with the custom-designed template."""
    if request.method == 'POST':
        username = request.POST.get('id', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.role == 'volunteer':
            login(request, user)
            return redirect('volunteer_dashboard')
        else:
            return render(request, 'users/volunteer_login.html', {
                'error': 'Invalid credentials or not a volunteer account.'
            })
    return render(request, 'users/volunteer_login.html')


@login_required
def volunteer_dashboard(request):
    """Volunteer's main dashboard: status, assigned pickups."""
    if request.user.role != 'volunteer':
        return redirect('dashboard')

    volunteer = get_object_or_404(Volunteer, user=request.user)

    from listings.models import PickupAssignment
    assignments = PickupAssignment.objects.filter(
        volunteer=volunteer
    ).select_related('claim', 'claim__listing', 'claim__listing__donor').order_by('-assigned_at')

    active_assignments = assignments.filter(status__in=['assigned', 'picked_up'])
    completed_assignments = assignments.filter(status='delivered')

    # Pre-process active assignments for template (short variable names)
    active_list = []
    for a in active_assignments:
        listing = a.claim.listing
        donor = listing.donor
        active_list.append({
            'id': a.id,
            'desc': listing.description,
            'ftype': listing.food_type,
            'ftype_display': listing.get_food_type_display(),
            'qty': listing.quantity_kg,
            'donor_name': getattr(donor, 'institution_name', '') or donor.username,
            'assigntime': a.assigned_at,
            'status': a.status,
            'pickup_instructions': getattr(listing, 'pickup_instructions', ''),
            'notes': a.notes if hasattr(a, 'notes') else '',
        })

    # Pre-process completed assignments for template
    completed_list = []
    for a in completed_assignments:
        listing = a.claim.listing
        donor = listing.donor
        completed_list.append({
            'id': a.id,
            'desc': listing.description,
            'donor_name': getattr(donor, 'institution_name', '') or donor.username,
            'qty': listing.quantity_kg,
            'assigntime': a.assigned_at,
        })

    return render(request, 'users/volunteer_dashboard.html', {
        'volunteer': volunteer,
        'active_assignments': active_assignments,
        'completed_assignments': completed_assignments,
        'active_list': active_list,
        'completed_list': completed_list,
        'active_count': len(active_list),
        'completed_count': len(completed_list),
    })


@login_required
def toggle_volunteer_status(request):
    """Toggle volunteer's active/inactive status."""
    if request.user.role != 'volunteer' or request.method != 'POST':
        return redirect('dashboard')

    volunteer = get_object_or_404(Volunteer, user=request.user)
    volunteer.status = 'inactive' if volunteer.status == 'active' else 'active'
    volunteer.save()
    return redirect('volunteer_dashboard')


@login_required
def update_pickup_status(request, assignment_id):
    """Volunteer marks a pickup as delivered.
    
    SECURITY: 'picked_up' status can ONLY be set via OTP verification.
    This view only allows transitioning from picked_up → delivered.
    """
    if request.user.role != 'volunteer' or request.method != 'POST':
        return redirect('dashboard')

    from listings.models import PickupAssignment
    assignment = get_object_or_404(PickupAssignment, id=assignment_id, volunteer__user=request.user)

    new_status = request.POST.get('status', '')

    # Block manual picked_up — must go through OTP verification
    if new_status == 'picked_up':
        messages.error(request, 'Food pickup must be verified with OTP from the restaurant.')
        return redirect('volunteer_dashboard')

    if new_status == 'delivered' and assignment.status == 'picked_up':
        assignment.status = 'delivered'
        assignment.save()

        # Mark the claim and listing as completed
        claim = assignment.claim
        claim.status = 'completed'
        claim.save()
        listing = claim.listing
        listing.status = 'completed'
        listing.save()
        messages.success(request, 'Delivery confirmed! Great work.')

    return redirect('volunteer_dashboard')


@login_required
@require_POST
def verify_pickup_otp(request, assignment_id):
    """Verify the 6-digit OTP to confirm food pickup.
    
    This is the ONLY way to transition an assignment to 'picked_up' status.
    """
    if request.user.role != 'volunteer':
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    from listings.models import PickupAssignment, PickupOTP
    from django.utils import timezone

    assignment = get_object_or_404(
        PickupAssignment,
        id=assignment_id,
        volunteer__user=request.user,
        status='assigned',
    )

    otp_code = request.POST.get('otp_code', '').strip()

    try:
        pickup_otp = assignment.otp
    except PickupOTP.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No OTP found for this assignment.'}, status=400)

    if pickup_otp.is_verified:
        return JsonResponse({'success': False, 'error': 'OTP has already been used.'}, status=400)

    if pickup_otp.code != otp_code:
        return JsonResponse({'success': False, 'error': 'Incorrect OTP. Please check with the restaurant.'}, status=400)

    # OTP is correct — mark verified and update assignment status
    pickup_otp.is_verified = True
    pickup_otp.verified_at = timezone.now()
    pickup_otp.save()

    assignment.status = 'picked_up'
    assignment.save()

    return JsonResponse({'success': True, 'message': 'OTP verified! Food marked as picked up.'})


# ======== EXISTING VIEWS ========

def ngo_directory(request):
    ngos = User.objects.filter(role='claimant')
    return render(request, 'users/ngo_directory.html', {'ngos': ngos})


def profile_view(request, user_id):
    user_profile = get_object_or_404(User, pk=user_id)
    impact_stats = {
        'meals_served': 1200 + (user_profile.id * 50),
        'volunteers': 5 + (user_profile.id % 20),
        'badges': ['Top Rated', 'Verified'] if user_profile.is_verified else []
    }
    return render(request, 'users/ngo_profile.html', {
        'profile_user': user_profile,
        'stats': impact_stats
    })


@login_required
def connected_ngos(request):
    if request.user.role != 'donor':
        return redirect('dashboard')

    from listings.models import Claim

    connected_claimants_ids = Claim.objects.filter(
        listing__donor=request.user,
        status__in=['approved', 'completed']
    ).values_list('claimant_id', flat=True).distinct()

    connected_ngos_list = User.objects.filter(id__in=connected_claimants_ids)

    return render(request, 'users/connected_ngos.html', {'ngos': connected_ngos_list})
