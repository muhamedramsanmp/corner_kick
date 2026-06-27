import random
import re
import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.messages import get_messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import cache_control, never_cache

from admin.admin_category.models import Category
from admin.admin_products.models import Product, Variant
from user.decorators import user_required
from user.user_wallet.models import Wallet

from .models import OTP, Referral, ReferralCode, ReferralReward
from .utils import (generate_referral_code, send_reset_password_otp,
                    send_signup_otp)

User = get_user_model()


import re


def validate_full_name(full_name):

    if not re.match(r"^[A-Za-z]+(?: [A-Za-z]+)*$", full_name):
        return "Name must contain only letters " "and spaces."

    return None


def validate_password_strength(password):

    errors = []

    password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$'

    if not re.match(password_regex, password):

        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")

        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter.")

        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter.")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character.")

    return errors


def signup_view(request):
    errors = {}

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        referral_code = request.POST.get("referral_code", "").strip().upper()
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        data = {
            "full_name": full_name,
            "email": email,
            "referral_code": referral_code,
        }

        if not full_name:
            errors["full_name"] = "Full name is required"
        elif validate_full_name(full_name):
            errors["full_name"] = validate_full_name(full_name)

        if not email:
            errors["email"] = "Email is required"

        if not password:
            errors["password"] = "Password is required"

        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match"

        if User.objects.filter(email=email).exists():
            errors["email"] = "Email already exists"

        if password:
            pwd_errors = validate_password_strength(password)

            if pwd_errors:
                errors["password"] = pwd_errors

        if errors:
            return render(request, "signup.html", {"errors": errors, "data": data})
        if referral_code:

            referral_obj = ReferralCode.objects.filter(code=referral_code).first()

            if not referral_obj:
                errors["referral_code"] = "Invalid referral code"

        if errors:
            return render(request, "signup.html", {"errors": errors, "data": data})

        otp = str(random.randint(100000, 999999))

        OTP.objects.filter(email=email, purpose="signup").delete()

        OTP.objects.create(email=email, code=otp, purpose="signup")

        request.session["signup_data"] = {
            "full_name": full_name,
            "email": email,
            "password": password,
            "referral_code": referral_code,
        }

        send_signup_otp(email=email, full_name=full_name, otp=otp)

        return redirect("verify_signup_otp")

    return render(request, "signup.html")


def login_view(request):

    if request.user.is_authenticated:

        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")

        if not email or not password:
            return render(
                request, "login.html", {"error": "Email and password are required."}
            )

        user = authenticate(request, username=email, password=password)

        if user is None:
            return render(
                request, "login.html", {"error": "Invalid email or password."}
            )

        if user.is_staff or user.is_superuser:
            return render(
                request, "login.html", {"error": "Admin must login from admin portal."}
            )

        if not user.is_active:
            return render(
                request, "login.html", {"error": "Your account has been blocked."}
            )

        login(request, user)
        return redirect("home")

    return render(request, "login.html")


@never_cache
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def home_view(request):

    if request.user.is_authenticated:

        if request.user.is_staff or request.user.is_superuser:

            return redirect("admin_dashboard")

    categories = Category.objects.filter(is_active=True)

    latest_products = (
        Product.objects.filter(
            is_deleted=False,
            is_active=True,
            category__is_deleted=False,
            category__is_active=True,
        )
        .prefetch_related("variants__images", "category")
        .order_by("-created_at")[:5]
    )

    context = {"categories": categories, "latest_products": latest_products}

    return render(request, "landingpage.html", context)


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with that email address.")
            return render(request, "forgotpassword.html")

        otp = str(random.randint(100000, 999999))

        OTP.objects.filter(email=email, purpose="reset").delete()

        OTP.objects.create(email=email, code=otp, purpose="reset")

        request.session["reset_email"] = email

        try:
            send_reset_password_otp(email=email, otp=otp)
        except Exception:
            messages.error(request, "Failed to send email.")
            return render(request, "forgotpassword.html")

        messages.success(request, "OTP sent to your email.")
        return redirect("verify_otp")

    return render(request, "forgotpassword.html")


def verify_otp(request):

    email = request.session.get("reset_email")

    if not email:
        return redirect("forgot_password")

    try:
        user = User.objects.get(email=email)

    except User.DoesNotExist:

        messages.error(request, "User not found")

        return redirect("forgot_password")

    otp_obj = (
        OTP.objects.filter(email=email, purpose="reset").order_by("-created_at").first()
    )

    time_left = otp_obj.time_left() if otp_obj else 60

    if request.method == "POST":

        entered_otp = (
            request.POST.get("otp1", "")
            + request.POST.get("otp2", "")
            + request.POST.get("otp3", "")
            + request.POST.get("otp4", "")
            + request.POST.get("otp5", "")
            + request.POST.get("otp6", "")
        )

        if len(entered_otp) != 6:

            messages.error(request, "Enter complete OTP")

            return render(request, "loginotpverify.html", {"time_left": time_left})

        otp_obj = (
            OTP.objects.filter(email=email, purpose="reset")
            .order_by("-created_at")
            .first()
        )
        if not otp_obj:

            messages.error(request, "OTP not found. Please resend.")

            return render(request, "loginotpverify.html", {"time_left": time_left})

        if otp_obj.is_expired():

            messages.error(request, "OTP expired.")

            return render(request, "loginotpverify.html", {"time_left": 0})

        if entered_otp != otp_obj.code:

            messages.error(request, "Invalid OTP.")

            return render(request, "loginotpverify.html", {"time_left": time_left})

        otp_obj.is_verified = True

        otp_obj.save()

        return redirect("reset_password")

    return render(request, "loginotpverify.html", {"time_left": time_left})


def resend_otp(request):
    email = request.session.get("reset_email")

    if not email:
        return redirect("forgot_password")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect("forgot_password")

    otp = str(secrets.randbelow(9000) + 1000)

    OTP.objects.filter(email=email, purpose="reset").delete()

    OTP.objects.create(email=email, code=otp, purpose="reset")

    send_reset_password_otp(email=email, otp=otp)

    messages.success(request, "New OTP sent.")
    return redirect("verify_otp")


def reset_password(request):
    email = request.session.get("reset_email")

    if not email:
        return redirect("forgot_password")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return redirect("forgot_password")

    otp_obj = (
        OTP.objects.filter(email=email, purpose="reset", is_verified=True)
        .order_by("-created_at")
        .first()
    )

    if not otp_obj:
        return redirect("verify_otp")

    if otp_obj.is_expired():
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if not password or not confirm_password:
            return render(
                request, "resetpassword.html", {"error": "All fields are required."}
            )

        if password != confirm_password:
            return render(
                request, "resetpassword.html", {"error": "Passwords do not match."}
            )

        errors = validate_password_strength(password)
        if errors:
            return render(request, "resetpassword.html", {"error": errors[0]})

        user.set_password(password)
        user.save()

        OTP.objects.filter(email=email, purpose="reset").delete()

        messages.success(request, "Password reset successful.")
        return redirect("login")

    return render(request, "resetpassword.html")


def verify_signup_otp(request):

    from django.contrib.messages import get_messages

    storage = get_messages(request)

    for _ in storage:
        pass

    data = request.session.get("signup_data")

    if not data:

        return redirect("signup")

    email = data.get("email")

    otp_obj = (
        OTP.objects.filter(email=email, purpose="signup")
        .order_by("-created_at")
        .first()
    )

    time_left = otp_obj.time_left() if otp_obj else 60

    if request.method == "POST":

        entered_otp = (
            request.POST.get("otp1", "")
            + request.POST.get("otp2", "")
            + request.POST.get("otp3", "")
            + request.POST.get("otp4", "")
            + request.POST.get("otp5", "")
            + request.POST.get("otp6", "")
        )

        if len(entered_otp) != 6:

            messages.error(request, "Enter complete OTP", extra_tags="otp")

            return render(request, "signup_verify.html", {"time_left": time_left})

        otp_obj = (
            OTP.objects.filter(email=email, purpose="signup")
            .order_by("-created_at")
            .first()
        )

        if not otp_obj:

            messages.error(request, "OTP not found", extra_tags="otp")

            return render(request, "signup_verify.html", {"time_left": time_left})

        if otp_obj.is_expired():

            messages.error(request, "OTP expired. Please resend.", extra_tags="otp")

            return render(request, "signup_verify.html", {"time_left": 0})

        if entered_otp != otp_obj.code:

            messages.error(request, "Invalid OTP", extra_tags="otp")

            return render(request, "signup_verify.html", {"time_left": time_left})

        full_name = data.get("full_name", "").strip()

        name_parts = full_name.split(" ", 1)

        first_name = name_parts[0]

        last_name = name_parts[1] if len(name_parts) > 1 else ""

        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            password=data["password"],
            first_name=first_name,
            last_name=last_name,
        )

        referral_code = data.get("referral_code")

        if referral_code:

            code_obj = ReferralCode.objects.filter(code=referral_code).first()

            if code_obj:

                Referral.objects.create(
                    referrer=code_obj.user,
                    referred_user=user,
                    referral_code=code_obj,
                    status="pending",
                )

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        otp_obj.delete()

        del request.session["signup_data"]

        messages.success(request, "Account created successfully")

        return redirect("home")

    return render(request, "signup_verify.html", {"time_left": time_left})


def resend_signup_otp(request):

    data = request.session.get("signup_data")

    if not data:
        return redirect("signup")

    email = data.get("email")

    otp = str(random.randint(100000, 999999))

    OTP.objects.filter(email=email, purpose="signup").delete()

    OTP.objects.create(email=email, code=otp, purpose="signup")

    full_name = data.get("full_name", "")

    send_signup_otp(email=email, full_name=full_name, otp=otp)

    messages.success(request, "New OTP sent successfully.")

    return redirect("verify_signup_otp")


@login_required
def referral_dashboard(request):

    referral_code, created = ReferralCode.objects.get_or_create(
        user=request.user, defaults={"code": generate_referral_code()}
    )

    referrals = (
        Referral.objects.filter(referrer=request.user)
        .select_related("referred_user")
        .prefetch_related("rewards")
        .order_by("-created_at")
    )

    paginator = Paginator(referrals, 5)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    reward_popup = request.session.pop("referral_reward", None)

    total_referrals = referrals.count()

    successful_referrals = referrals.filter(status="completed").count()

    total_earned = (
        ReferralReward.objects.filter(user=request.user, status="credited").aggregate(
            total=Sum("reward_amount")
        )["total"]
        or 0
    )
    wallet, created = Wallet.objects.get_or_create(user=request.user)

    context = {
        "referral_code": referral_code,
        "referrals": referrals,
        "referrals": page_obj,
        "page_obj": page_obj,
        "successful_referrals": successful_referrals,
        "total_earned": total_earned,
        "wallet": wallet,
        "reward_popup": reward_popup,
        "total_referrals": total_referrals,
    }

    return render(request, "referral.html", context)


@login_required
def mark_reward_seen(request, reward_id):

    reward = ReferralReward.objects.filter(id=reward_id, user=request.user).first()

    if reward:

        reward.is_seen = True
        reward.save()

    return JsonResponse({"success": True})


from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render

from .models import ContactMessage


def about_page(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        user_message = request.POST.get("message")

        ContactMessage.objects.create(
            name=name,
            email=email,
            phone=phone,
            message=user_message,
        )

        send_mail(
            subject=f"Corner Kick Contact Form - {name}",
            message=(
                f"Name: {name}\n\n"
                f"Email: {email}\n\n"
                f"Phone: {phone}\n\n"
                f"Message:\n{user_message}"
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=["cornerkick1010@gmail.com"],
            fail_silently=False,
        )

        messages.success(request, "Your message has been sent successfully.")

        return redirect("about")

    return render(request, "about.html")
