import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache,cache_control
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
import secrets


User = get_user_model()


def validate_password_strength(password):
    """
    Returns a list of error messages if password is weak.
    Returns an empty list if password is strong.
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter (A-Z).")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter (a-z).")

    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number (0-9).")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character (!@#$%^&* etc).")

    return errors

def signup_view(request):
    """Handle user registration."""

    # 🔥 Prevent logged-in users from accessing signup
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        # --- Validation ---
        if not all([full_name, email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return redirect("signup")

        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            messages.error(request, "Enter a valid email address.")
            return redirect("signup")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")

        # --- Strong Password Check ---
        password_errors = validate_password_strength(password)
        if password_errors:
            for error in password_errors:
                messages.error(request, error)
            return redirect("signup")

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect("signup")

        # --- Create User ---
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        messages.success(request, "Account created successfully. Please log in.")
        return redirect("login")

    return render(request, "signup.html")

def login_view(request):

    # 🔥 Prevent logged-in users from accessing login page
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")

        if not email or not password:
            messages.error(request, "Email and password are required.")
            return redirect("login")

        user = authenticate(request, username=email, password=password)

        if user is None:
            messages.error(request, "Invalid email or password.")
            return redirect("login")

        login(request, user)
        messages.success(request, "Login successful.")
        return redirect("home")

    return render(request, "login.html")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login")
def home_view(request):
    return render(request, "landingpage.html")


@never_cache
@login_required(login_url="login")
def logout_view(request):
    logout(request)
    request.session.flush() 
    messages.success(request, "Logged out successfully.")
    return redirect("login")

# ─────────────────────────────────────────
# STEP 1 — Forgot Password (Email Entry)
# ─────────────────────────────────────────
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with that email address.")
            return render(request, "forgotpassword.html")

        # Generate OTP
        otp = str(secrets.randbelow(9000) + 1000)

        # Store in session
        request.session["reset_otp"] = otp
        request.session["reset_email"] = email
        request.session["otp_verified"] = False

        # 🔥 SEND EMAIL
        subject = "Your Password Reset OTP"
        message = f"Your OTP for password reset is: {otp}"
        from_email = "cornerkick1010@gmail.com"
        recipient_list = [email]

        try:
            send_mail(subject, message, from_email, recipient_list)
        except Exception as e:
            messages.error(request, "Failed to send email. Check email configuration.")
            return render(request, "forgotpassword.html")

        messages.success(request, "OTP has been sent to your email.")
        return redirect("verify_otp")

    return render(request, "forgotpassword.html")
def verify_otp(request):
    if not request.session.get("reset_email"):
        messages.error(request, "Please start the password reset process first.")
        return redirect("forgot_password")

    if request.method == "POST":
        otp1 = request.POST.get("otp1", "")
        otp2 = request.POST.get("otp2", "")
        otp3 = request.POST.get("otp3", "")
        otp4 = request.POST.get("otp4", "")
        entered_otp = otp1 + otp2 + otp3 + otp4

        stored_otp = request.session.get("reset_otp", "")

        if entered_otp == stored_otp:
            request.session["otp_verified"] = True
            return redirect("reset_password")
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(request, "loginotpverify.html")

    return render(request, "loginotpverify.html")


from django.core.mail import send_mail
from django.conf import settings
import secrets

def resend_otp(request):
    email = request.session.get("reset_email")

    if not email:
        messages.error(request, "Session expired. Try again.")
        return redirect("forgot_password")

    # Generate new OTP
    otp = str(secrets.randbelow(9000) + 1000)

    request.session["reset_otp"] = otp
    request.session["otp_verified"] = False

    # Send email
    send_mail(
        "Your New OTP",
        f"Your new OTP is: {otp}",
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )

    messages.success(request, "New OTP sent.")
    return redirect("verify_otp")


# ─────────────────────────────────────────
# STEP 3 — Reset Password
# ─────────────────────────────────────────
def reset_password(request):
    if not request.session.get("otp_verified"):
        messages.error(request, "Please verify your OTP first.")
        return redirect("forgot_password")

    if request.method == "POST":
        password         = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "resetpassword.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "resetpassword.html")

        has_upper   = any(c.isupper() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password)

        if not has_upper or not has_special:
            messages.error(request, "Password must contain at least one uppercase letter and one special character.")
            return render(request, "resetpassword.html")

        email = request.session.get("reset_email")
        try:
            user = User.objects.get(email=email)
            user.password = make_password(password)
            user.save()
        except User.DoesNotExist:
            messages.error(request, "User not found. Please restart the process.")
            return redirect("forgot_password")

        # Clean up session
        request.session.pop("reset_otp",    None)
        request.session.pop("reset_email",  None)
        request.session.pop("otp_verified", None)

        messages.success(request, "Password reset successful! You can now log in.")
        return redirect("login")

    return render(request, "resetpassword.html")
