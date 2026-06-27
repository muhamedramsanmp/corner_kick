from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from user.accounts.models import Profile
from user.decorators import user_required

from .models import Address


@user_required
def address_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    addresses = Address.objects.filter(user=request.user).order_by("-id")

    return render(request, "address.html", {"addresses": addresses, "profile": profile})


@login_required
def add_address(request):

    next_page = request.GET.get("next")
    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        state = request.POST.get("state", "").strip()
        city = request.POST.get("city", "").strip()
        country = request.POST.get("country", "").strip()
        address_line = request.POST.get("address_line", "").strip()
        address_type = request.POST.get("address_type", "").strip()
        is_default = True if request.POST.get("is_default") else False

        if not all([full_name, phone, pincode, state, city, address_line]):
            messages.error(request, "Please fill all fields.")
            return render(
                request,
                "add_address.html",
                {
                    "full_name": full_name,
                    "phone": phone,
                    "pincode": pincode,
                    "state": state,
                    "city": city,
                    "address_line": address_line,
                    "address_type": address_type,
                },
            )

        if len(phone) != 10:
            messages.error(request, "Enter a valid 10-digit phone number.")
            return render(request, "add_address.html")

        if len(pincode) != 6:
            messages.error(request, "Enter a valid 6-digit pincode.")
            return render(request, "add_address.html")

        if is_default:
            Address.objects.filter(user=request.user, is_default=True).update(
                is_default=False
            )

        Address.objects.create(
            user=request.user,
            full_name=full_name,
            phone=phone,
            pincode=pincode,
            state=state,
            city=city,
            country=country,
            address_line=address_line,
            address_type=address_type,
            is_default=is_default,
        )

        if next_page == "checkout":

            return redirect("checkout_page")

        return redirect("addressinfo:address_view")

    return render(request, "add_address.html", {"next": next_page})


def delete_address(request, id):

    address = Address.objects.filter(id=id, user=request.user).first()

    if not address:
        return redirect("addressinfo:address_view")

    if request.method == "POST":
        address.delete()
        return redirect("addressinfo:address_view")

    addresses = Address.objects.filter(user=request.user)

    return render(request, "delete_address.html", {"addresses": addresses})


@login_required(login_url="login")
def edit_address(request, id):

    address = get_object_or_404(Address, id=id, user=request.user)

    next_page = request.GET.get("next")
    if request.method == "POST":

        address.full_name = request.POST.get("full_name")
        address.phone = request.POST.get("phone")
        address.city = request.POST.get("city")
        address.pincode = request.POST.get("pincode")
        address.state = request.POST.get("state")
        address.country = request.POST.get("country")
        address.address_line = request.POST.get("address_line")

        address.address_type = request.POST.get("address_type") or "home"

        if request.POST.get("is_default"):
            Address.objects.filter(user=request.user, is_default=True).exclude(
                id=address.id
            ).update(is_default=False)

            address.is_default = True
        else:
            address.is_default = False

        address.save()

        if next_page == "checkout":

            return redirect("checkout_page")
        messages.success(request, "address updated.")
        return redirect("addressinfo:address_view")

    return render(request, "edit_address.html", {"address": address, "next": next_page})
