import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache,cache_control
from django.core.mail import send_mail
import secrets
from django.conf import settings
from django.utils import timezone
from .models import OTP
import random
import time 
from django.contrib.messages import get_messages
from admin.admin_category.models import Category
from admin.admin_products.models import Product,Variant
from user.decorators import user_required
from .utils import generate_referral_code
from .models import ReferralCode,Referral,ReferralReward
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum
from user.user_wallet.models import Wallet
from django.http import JsonResponse
from django.core.paginator import Paginator

User = get_user_model()


def validate_password_strength(password):

    errors = []

    # single strong password regex
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
        referral_code = request.POST.get("referral_code","").strip().upper()
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")


        # store old values
        data = {
            "full_name": full_name,
            "email": email,
            "referral_code": referral_code,
        }

        # required
        if not full_name:
            errors["full_name"] = "Full name is required"

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
            return render(request, "signup.html", {
                "errors": errors,
                "data": data
            })
        if referral_code:

            referral_obj = ReferralCode.objects.filter(
                code=referral_code
            ).first()

            if not referral_obj:

                errors["referral_code"] = (
                    "Invalid referral code"
                )

        # ✅ OTP only if everything valid
        otp = str(random.randint(100000, 999999))

        # 🔥 SAVE OTP IN DATABASE
        OTP.objects.filter(email=email, purpose='signup').delete()
        OTP.objects.create(
            email=email,
            code=otp,
            purpose='signup'
        )

        # 🔥 store ONLY required data (NO OTP here)
        request.session["signup_data"] = {
            "full_name": full_name,
            "email": email,
            "password": password,
            "referral_code": referral_code,
        }

        # 🔥 send OTP
        send_mail(
            "Your OTP Code",
            f"Your OTP is {otp}",
            "your_email@gmail.com",
            [email],
            fail_silently=False,
        )

        return redirect("verify_signup_otp")

    return render(request, "signup.html")

def login_view(request):


    if request.user.is_authenticated:

        return redirect(
            "home"
        )

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")

        if not email or not password:
            return render(request, "login.html", {
                "error": "Email and password are required."
            })

        user = authenticate(request, username=email, password=password)

        if user is None:
            return render(request, "login.html", {
                "error": "Invalid email or password."
            })

        # 🔒 BLOCK ADMIN LOGIN
        if user.is_staff or user.is_superuser:
            return render(request, "login.html", {
                "error": "Admin must login from admin portal."
            })

        # 🔒 BLOCK INACTIVE USERS
        if not user.is_active:
            return render(request, "login.html", {
                "error": "Your account has been blocked."
            })

        login(request, user)
        return redirect("home")

    return render(request, "login.html")


@never_cache
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def home_view(request):

    # =====================================
    # BLOCK ADMIN FROM FRONTEND
    # =====================================

    if request.user.is_authenticated:

        if request.user.is_staff or request.user.is_superuser:

            return redirect(
                "admin_dashboard"
            )

    categories = Category.objects.filter(
        is_active=True
    )

    latest_products = Product.objects.filter(

        is_deleted=False,

        is_active=True,

        category__is_deleted=False,

        category__is_active=True,

    ).prefetch_related(

        'variants__images',

        'category'

    ).order_by(

        '-created_at'

    )[:5]

    context = {

        'categories': categories,

        'latest_products': latest_products

    }

    return render(

        request,

        'landingpage.html',

        context

    )




def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        # ❌ user not found
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "No account found with that email address.")
            return render(request, "forgotpassword.html")

        # 🔥 generate OTP
        otp = str(random.randint(100000, 999999))

        # 🔥 delete old reset OTPs
        OTP.objects.filter(email=email, purpose='reset').delete()

        # 🔥 create new OTP
        OTP.objects.create(
            email=email,
            code=otp,
            purpose='reset'
        )

        # 🔥 store ONLY email (NOT OTP)
        request.session["reset_email"] = email

        # 🔥 send email
        try:
            send_mail(
                "Your Password Reset OTP",
                f"Your OTP is: {otp}",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
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


    # 🔥 GET LATEST OTP
    otp_obj = OTP.objects.filter(
        email=email,
        purpose='reset'
    ).order_by('-created_at').first()


    # 🔥 TIMER VALUE
    time_left = otp_obj.time_left() if otp_obj else 60


    if request.method == "POST":

        entered_otp = (
            request.POST.get("otp1", "") +
            request.POST.get("otp2", "") +
            request.POST.get("otp3", "") +
            request.POST.get("otp4", "") +
            request.POST.get("otp5", "") +
            request.POST.get("otp6", "")
        )


        # ❌ incomplete OTP
        if len(entered_otp) != 6:

            messages.error(request, "Enter complete OTP")

            return render(request, "loginotpverify.html", {
                "time_left": time_left
            })


        # 🔥 GET LATEST OTP AGAIN
        otp_obj = OTP.objects.filter(
            email=email,
            purpose='reset'
        ).order_by('-created_at').first()


        # ❌ no OTP
        if not otp_obj:

            messages.error(request, "OTP not found. Please resend.")

            return render(request, "loginotpverify.html", {
                "time_left": time_left
            })


        # ❌ expired
        if otp_obj.is_expired():

            messages.error(request, "OTP expired.")

            return render(request, "loginotpverify.html", {
                "time_left": 0
            })


        # ❌ incorrect
        if entered_otp != otp_obj.code:

            messages.error(request, "Invalid OTP.")

            return render(request, "loginotpverify.html", {
                "time_left": time_left
            })


        # ✅ VERIFIED
        otp_obj.is_verified = True

        otp_obj.save()


        return redirect("reset_password")


    return render(request, "loginotpverify.html", {
        "time_left": time_left
    })

def resend_otp(request):
    email = request.session.get("reset_email")

    if not email:
        return redirect("forgot_password")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect("forgot_password")

    # 🔥 generate new OTP
    otp = str(secrets.randbelow(9000) + 1000)

    # 🔥 delete old OTP (only reset purpose)
    OTP.objects.filter(email=email, purpose='reset').delete()

    # 🔥 create new OTP
    OTP.objects.create(
        email=email,
        code=otp,
        purpose='reset'
    )

    # 🔥 send email
    send_mail(
        "New OTP",
        f"Your OTP is: {otp}",
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )

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

    # 🔥 check verified OTP
    otp_obj = OTP.objects.filter(
        email=email,
        purpose='reset',
        is_verified=True
    ).order_by('-created_at').first()

    if not otp_obj:
        return redirect("verify_otp")

    if otp_obj.is_expired():
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        # ❌ STEP 1: empty
        if not password or not confirm_password:
            return render(request, "resetpassword.html", {
                "error": "All fields are required."
            })

        # ❌ STEP 2: mismatch
        if password != confirm_password:
            return render(request, "resetpassword.html", {
                "error": "Passwords do not match."
            })

        # ❌ STEP 3: strength (one-by-one)
        errors = validate_password_strength(password)
        if errors:
            return render(request, "resetpassword.html", {
                "error": errors[0]
            })

        # ✅ STEP 4: success
        user.set_password(password)
        user.save()

        OTP.objects.filter(email=email, purpose='reset').delete()

        messages.success(request, "Password reset successful.")
        return redirect("login")

    return render(request, "resetpassword.html")


def verify_signup_otp(request):

    from django.contrib.messages import get_messages

    storage = get_messages(request)

    for _ in storage:
        pass

    # =====================================
    # SESSION DATA
    # =====================================

    data = request.session.get(
        "signup_data"
    )

    if not data:

        return redirect(
            "signup"
        )

    email = data.get("email")

    # =====================================
    # GET OTP
    # =====================================

    otp_obj = OTP.objects.filter(

        email=email,

        purpose='signup'

    ).order_by(

        '-created_at'

    ).first()

    time_left = (
        otp_obj.time_left()
        if otp_obj else 60
    )

    # =====================================
    # POST
    # =====================================

    if request.method == "POST":

        entered_otp = (

            request.POST.get("otp1", "") +

            request.POST.get("otp2", "") +

            request.POST.get("otp3", "") +

            request.POST.get("otp4", "") +

            request.POST.get("otp5", "") +

            request.POST.get("otp6", "")

        )

        # =====================================
        # VALIDATE LENGTH
        # =====================================

        if len(entered_otp) != 6:

            messages.error(

                request,

                "Enter complete OTP",

                extra_tags="otp"

            )

            return render(

                request,

                "signup_verify.html",

                {

                    "time_left": time_left

                }

            )

        # =====================================
        # FETCH OTP AGAIN
        # =====================================

        otp_obj = OTP.objects.filter(

            email=email,

            purpose='signup'

        ).order_by(

            '-created_at'

        ).first()

        # =====================================
        # OTP NOT FOUND
        # =====================================

        if not otp_obj:

            messages.error(

                request,

                "OTP not found",

                extra_tags="otp"

            )

            return render(

                request,

                "signup_verify.html",

                {

                    "time_left": time_left

                }

            )

        # =====================================
        # OTP EXPIRED
        # =====================================

        if otp_obj.is_expired():

            messages.error(

                request,

                "OTP expired. Please resend.",

                extra_tags="otp"

            )

            return render(

                request,

                "signup_verify.html",

                {

                    "time_left": 0

                }

            )

        # =====================================
        # INVALID OTP
        # =====================================

        if entered_otp != otp_obj.code:

            messages.error(

                request,

                "Invalid OTP",

                extra_tags="otp"

            )

            return render(

                request,

                "signup_verify.html",

                {

                    "time_left": time_left

                }

            )

        # =====================================
        # CREATE USER
        # =====================================

        full_name = data.get(
            "full_name",
            ""
        ).strip()

        name_parts = full_name.split(" ", 1)

        first_name = name_parts[0]

        last_name = (
            name_parts[1]
            if len(name_parts) > 1
            else ""
        )

        user = User.objects.create_user(

            username=data["email"],

            email=data["email"],

            password=data["password"],

            first_name=first_name,

            last_name=last_name

        )
        # =====================================
        # CREATE REFERRAL RECORD
        # =====================================

        referral_code = data.get(
            "referral_code"
        )

        if referral_code:

            code_obj = ReferralCode.objects.filter(
                code=referral_code
            ).first()

            if code_obj:

                Referral.objects.create(

                    referrer=code_obj.user,

                    referred_user=user,

                    referral_code=code_obj,

                    status="pending"

                )

        # =====================================
        # LOGIN USER
        # =====================================

        login(

            request,

            user,

            backend='django.contrib.auth.backends.ModelBackend'

        )

        # =====================================
        # DELETE OTP
        # =====================================

        otp_obj.delete()

        # =====================================
        # CLEAR SESSION
        # =====================================

        del request.session["signup_data"]

        # =====================================
        # SUCCESS MESSAGE
        # =====================================

        messages.success(

            request,

            "Account created successfully"

        )

        # =====================================
        # REDIRECT
        # =====================================

        return redirect(
            "home"
        )

    # =====================================
    # GET REQUEST
    # =====================================

    return render(

        request,

        "signup_verify.html",

        {

            "time_left": time_left

        }

    )

def resend_signup_otp(request):
    data = request.session.get("signup_data")

    if not data:
        return redirect("signup")

    email = data.get("email")

    # generate new OTP
    otp = str(random.randint(100000, 999999))

    # delete old OTP
    OTP.objects.filter(email=email, purpose='signup').delete()

    # create new OTP
    OTP.objects.create(
        email=email,
        code=otp,
        purpose='signup'
    )

    # send mail
    send_mail(
        "Your OTP Code",
        f"Your new OTP is {otp}",
        "your_email@gmail.com",
        [email],
        fail_silently=False,
    )

    messages.success(request, "New OTP sent successfully.")
    return redirect("verify_signup_otp")



@login_required
def referral_dashboard(request):

    referral_code, created = ReferralCode.objects.get_or_create(
        user=request.user,
        defaults={
            "code": generate_referral_code()
        }
    )

    referrals = Referral.objects.filter(
        referrer=request.user
    ).select_related(
        "referred_user"
    ).prefetch_related(
        "rewards"
    ).order_by(
        "-created_at"
    )

    paginator = Paginator(
        referrals,
        5
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )
    print(
        request.session.get(
            "referral_reward"
        )
    )

    reward_popup = request.session.pop(
        "referral_reward",
        None
    )

    successful_referrals = referrals.filter(
        status='completed'
    ).count()

    total_earned = ReferralReward.objects.filter(
        user=request.user,
        status='credited'
    ).aggregate(
        total=Sum('reward_amount')
    )['total'] or 0
    wallet, created = Wallet.objects.get_or_create(
        user=request.user
    )

    context = {
        "referral_code": referral_code,
        "referrals": referrals,
        "referrals": page_obj,
         "page_obj": page_obj,
        "successful_referrals": successful_referrals,
        "total_earned": total_earned,
        "wallet": wallet,
        "reward_popup":reward_popup
    }

    return render(
        request,
        "referral.html",
        context
    )



@login_required
def mark_reward_seen(request, reward_id):

    reward = ReferralReward.objects.filter(

        id=reward_id,

        user=request.user

    ).first()

    if reward:

        reward.is_seen = True
        reward.save()

    return JsonResponse({
        "success": True
    })