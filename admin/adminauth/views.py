from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.cache import never_cache
from django.contrib.auth import logout


User = get_user_model()

@never_cache
def admin_login(request):

    # ✅ BLOCK access if already logged in
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, "You are not authorized as admin.")
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "admin_login.html")


@never_cache
@login_required(login_url='admin_login')
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')

@never_cache
def admin_logout(request):
    logout(request)   # ✅ clears session
    messages.success(request, "You have been logged out successfully")
    return redirect('admin_login')



@login_required(login_url='admin_login')
def user_management(request):

    query = request.GET.get('q', '').strip()

    users_list = User.objects.filter(is_staff=False).order_by('-id')

    # 🔥 IMPROVED SEARCH (multi-field + startswith behavior)
    if query:
        users_list = users_list.filter(
            Q(username__istartswith=query) |
            Q(email__istartswith=query) |
            Q(first_name__istartswith=query) |
            Q(last_name__istartswith=query)
        )

    paginator = Paginator(users_list, 5)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    # stats based on filtered result
    total_users = users_list.count()
    active_users = users_list.filter(is_active=True).count()
    banned_users = users_list.filter(is_active=False).count()

    today = timezone.localdate()
    new_today = users_list.filter(date_joined__date=today).count()

    return render(request, 'user_management.html', {
        'users': users,
        'query': query,   # 🔥 IMPORTANT (to keep value in search box)
        'total_users': total_users,
        'active_users': active_users,
        'banned_users': banned_users,
        'new_today': new_today,
    })



def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user.is_staff:
        messages.error(request, "Cannot modify admin user.")
        return redirect('user_management')

    user.is_active = not user.is_active
    user.save()

    # 👇 Better message (with user info)
    name = f"{user.first_name} {user.last_name}".strip() or user.email

    if user.is_active:
        messages.success(request, f"{name} has been activated")
    else:
        messages.error(request, f"{name} has been blocked")

    return redirect('user_management')