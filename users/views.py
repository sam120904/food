import secrets
import string

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
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
                except Exception:
                    pass  # Don't block volunteer creation if email fails

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

    return render(request, 'users/volunteer_dashboard.html', {
        'volunteer': volunteer,
        'active_assignments': active_assignments,
        'completed_assignments': completed_assignments,
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
    """Volunteer marks a pickup as picked_up or delivered."""
    if request.user.role != 'volunteer' or request.method != 'POST':
        return redirect('dashboard')

    from listings.models import PickupAssignment
    assignment = get_object_or_404(PickupAssignment, id=assignment_id, volunteer__user=request.user)

    new_status = request.POST.get('status', '')
    if new_status in ('picked_up', 'delivered'):
        assignment.status = new_status
        assignment.save()

        # If delivered, mark the claim as completed
        if new_status == 'delivered':
            claim = assignment.claim
            claim.status = 'completed'
            claim.save()
            listing = claim.listing
            listing.status = 'completed'
            listing.save()

    return redirect('volunteer_dashboard')


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
