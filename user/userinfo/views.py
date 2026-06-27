import os
import random
import re
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (get_user_model, logout,
                                 update_session_auth_hash)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from user.accounts.models import Profile
from user.accounts.utils import send_reset_password_otp
from user.decorators import user_required

from .models import PasswordResetOTP

User = get_user_model()


def validate_full_name(full_name):

    if not re.match(r"^[A-Za-z]+(?: [A-Za-z]+)*$", full_name):
        return "Name must contain only letters " "and spaces."

    return None


def validate_password_strength(password):
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")

    if not re.search(r"[A-Z]", password):
        errors.append("At least one uppercase letter required.")

    if not re.search(r"[a-z]", password):
        errors.append("At least one lowercase letter required.")

    if not re.search(r"\d", password):
        errors.append("At least one number required.")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("At least one special character required.")

    return errors


User = get_user_model()


@never_cache
@user_required
def profile_view(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not email:
            messages.error(request, "Email is required")
            return redirect("userinfo:profile")

        if User.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, "Email already exists")
            return redirect("userinfo:profile")

        if full_name:
            parts = full_name.split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""

        user.email = email
        user.save()

        profile.phone = phone
        profile.save()

        messages.success(request, "Profile updated successfully")
        return redirect("userinfo:profile")

    return render(
        request,
        "profile.html",
        {
            "user": user,
            "profile": profile,
        },
    )


@login_required(login_url="login")
def edit_profile(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        image = request.FILES.get("profile_image")

        if full_name:

            name_error = validate_full_name(full_name)

            if name_error:
                messages.error(request, name_error)
                return redirect("userinfo:edit_profile")
        if phone:

            if not phone.isdigit():

                messages.error(request, "Phone number must contain only digits")

                return redirect("userinfo:edit_profile")

            if len(phone) != 10:

                messages.error(request, "Phone number must be exactly 10 digits")

                return redirect("userinfo:edit_profile")

        profile.phone = phone
        profile.save()

        if not email:
            messages.error(request, "Email is required")
            return redirect("userinfo:edit_profile")

        if User.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, "Email already exists")
            return redirect("userinfo:edit_profile")

        if full_name:
            parts = full_name.split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""

        if email != user.email:

            request.session["new_email"] = email

            otp = str(random.randint(100000, 999999))

            PasswordResetOTP.objects.filter(user=user).delete()

            PasswordResetOTP.objects.create(user=user, otp=otp)

            send_mail(
                "Corner Kick - Email Verification OTP",
                (
                    f"Hello {full_name},\n\n"
                    f"You requested to change your email address.\n\n"
                    f"Your verification OTP is:\n\n"
                    f"{otp}\n\n"
                    f"OTP Expiry: 60 seconds\n\n"
                    f"If you did not request this change, "
                    f"please ignore this email.\n\n"
                    f"Regards,\n"
                    f"Corner Kick Team"
                ),
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )

            return redirect("userinfo:change_email_verify")

        user.save()

        profile.phone = phone
        profile.save()

        remove_image = request.POST.get("remove_image")

        if remove_image:
            if profile.image:
                try:
                    if os.path.exists(profile.image.path):
                        os.remove(profile.image.path)
                except:
                    pass
            profile.image = None

        elif image:
            if profile.image:
                try:
                    if os.path.exists(profile.image.path):
                        os.remove(profile.image.path)
                except:
                    pass

            profile.image = image

        profile.save()

        messages.success(request, "Profile updated successfully")
        return redirect("userinfo:profile")

    return render(request, "edit_profile.html", {"profile": profile, "user": user})


@login_required
def change_email_verify(request):
    new_email = request.session.get("new_email")

    if not new_email:
        return redirect("userinfo:edit_profile")

    otp_obj = (
        PasswordResetOTP.objects.filter(user=request.user)
        .order_by("-created_at")
        .first()
    )

    time_left = otp_obj.time_left() if otp_obj else 60

    if request.method == "POST":

        entered_otp = "".join([request.POST.get(f"otp{i}", "") for i in range(1, 7)])

        if not otp_obj:
            return render(
                request,
                "change_emailverify.html",
                {"error": "OTP not found", "time_left": time_left},
            )

        if otp_obj.is_expired():
            return render(
                request,
                "change_emailverify.html",
                {"error": "OTP expired", "time_left": 0},
            )

        if entered_otp != otp_obj.otp:
            return render(
                request,
                "change_emailverify.html",
                {"error": "Invalid OTP", "time_left": time_left},
            )

        user = request.user
        user.email = new_email
        user.save()

        PasswordResetOTP.objects.filter(user=user).delete()

        request.session.pop("new_email", None)

        return redirect("userinfo:profile")

    return render(request, "change_emailverify.html", {"time_left": time_left})


@login_required
def resend_change_email_otp(request):
    user = request.user
    new_email = request.session.get("new_email")

    if not new_email:
        return redirect("userinfo:edit_profile")

    otp = str(random.randint(100000, 999999))

    PasswordResetOTP.objects.filter(user=user).delete()

    PasswordResetOTP.objects.create(user=user, otp=otp)

    send_mail(
        "Corner Kick - Email Verification OTP",
        (
            f"Hello {user.get_full_name()},\n\n"
            f"You requested to change your email address.\n\n"
            f"Your verification OTP is:\n\n"
            f"{otp}\n\n"
            f"OTP Expiry: 60 seconds\n\n"
            f"If you did not request this change, "
            f"please ignore this email.\n\n"
            f"Regards,\n"
            f"Corner Kick Team"
        ),
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )

    return redirect("userinfo:change_email_verify")


@never_cache
def logout_page(request):
    return render(request, "logout.html")


@never_cache
def logout_user(request):

    if request.method == "POST":

        logout(request)
        request.session.flush()

        messages.success(request, "Logged out successfully")

        return redirect("login")


@login_required(login_url="login")
def change_password(request):

    if request.method == "POST":

        user = request.user

        old_password = request.POST.get("old_password", "").strip()
        new_password = request.POST.get("new_password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        if not user.check_password(old_password):
            messages.error(
                request,
                "Current password is incorrect",
                extra_tags="password",
            )
            return redirect("userinfo:change_password")

        if not new_password:
            messages.error(
                request,
                "New password cannot be empty",
                extra_tags="password",
            )
            return redirect("userinfo:change_password")

        password_errors = validate_password_strength(new_password)

        if password_errors:
            for error in password_errors:
                messages.error(
                    request,
                    error,
                    extra_tags="password",
                )
            return redirect("userinfo:change_password")

        if new_password != confirm_password:
            messages.error(
                request,
                "Passwords do not match",
                extra_tags="password",
            )
            return redirect("userinfo:change_password")

        if old_password == new_password:
            messages.error(
                request,
                "New password cannot be the same as the current password.",
                extra_tags="password",
            )
            return redirect("userinfo:change_password")

        user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user)

        messages.success(
            request,
            "Password updated successfully.",
            extra_tags="password",
        )

        return redirect("userinfo:profile")

    return render(request, "change_password.html")


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with that email.")
            return render(request, "forgot_password.html")

        otp = str(secrets.randbelow(900000) + 100000)

        PasswordResetOTP.objects.filter(user=user).delete()

        PasswordResetOTP.objects.create(user=user, otp=otp)

        # store only email
        request.session["reset_email"] = email

        # send email
        send_reset_password_otp(email=email, otp=otp)

        messages.success(request, "OTP sent to your email.")
        return redirect("userinfo:profile_verify_otp")

    return render(request, "forgot_password.html")


@never_cache
def profile_verify_otp(request):
    email = request.session.get("reset_email")

    if not email:
        return redirect("userinfo:forgot_password")

    user = User.objects.filter(email=email).first()
    if not user:
        return redirect("userinfo:forgot_password")

    otp_obj = PasswordResetOTP.objects.filter(user=user).order_by("-created_at").first()

    time_left = otp_obj.time_left() if otp_obj else 60

    if request.method == "POST":
        entered_otp = "".join([request.POST.get(f"otp{i}", "") for i in range(1, 7)])

        otp_obj = (
            PasswordResetOTP.objects.filter(user=user, otp=entered_otp)
            .order_by("-created_at")
            .first()
        )

        if not otp_obj:
            return render(
                request,
                "verify_otp.html",
                {"error": "Invalid OTP", "time_left": time_left},
            )

        if otp_obj.is_expired():
            return render(
                request, "verify_otp.html", {"error": "OTP expired", "time_left": 0}
            )

        otp_obj.is_verified = True
        otp_obj.save()

        request.session["otp_verified"] = True

        return redirect("userinfo:reset_password")

    return render(request, "verify_otp.html", {"time_left": time_left})


@never_cache
def resend_otp(request):
    email = request.session.get("reset_email")

    if not email:
        return redirect("userinfo:forgot_password")

    user = User.objects.get(email=email)

    otp = str(secrets.randbelow(900000) + 100000)

    PasswordResetOTP.objects.filter(user=user).delete()
    PasswordResetOTP.objects.create(user=user, otp=otp)

    send_reset_password_otp(email=email, otp=otp)

    messages.success(request, "New OTP sent.")
    return redirect("userinfo:profile_verify_otp")


@never_cache
def reset_password(request):
    email = request.session.get("reset_email")

    if not email:
        return redirect("userinfo:forgot_password")

    user = User.objects.get(email=email)

    otp_obj = PasswordResetOTP.objects.filter(user=user, is_verified=True).first()

    if not otp_obj:
        messages.error(request, "OTP not verified.")
        return redirect("userinfo:profile_verify_otp")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "reset_password.html")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "reset_password.html")

        user.set_password(password)
        user.save()

        PasswordResetOTP.objects.filter(user=user).delete()
        request.session.flush()

        messages.success(request, "Password reset successful.")
        return redirect("login")

    return render(request, "reset_password.html")
