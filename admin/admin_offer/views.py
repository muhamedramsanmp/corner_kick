from django.shortcuts import render,redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from admin.decorators import admin_required
from .models import Offer
from django.contrib import messages
from .models import (
    Offer,
    OfferProduct,
    CategoryOffer
)
from user.products.models import Product
from admin.admin_category.models import Category
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError




@admin_required
def offer_management(request):

    search = request.GET.get(
        "search",
        ""
    )

    status = request.GET.get(
        "status",
        ""
    )

    offer_type = request.GET.get(
        "type",
        ""
    )

    offers = Offer.objects.filter(

        is_deleted=False

    ).order_by(

        "-id"

    )

    if search:

        offers = offers.filter(

            Q(offer_name__icontains=search)

        )

    if offer_type:

        offers = offers.filter(

            apply_to=offer_type

        )

    today = timezone.now().date()

    if status == "active":

        offers = offers.filter(

            is_active=True,

            start_date__lte=today,

            end_date__gte=today

        )

    elif status == "expired":

        offers = offers.filter(

            end_date__lt=today

        )

    paginator = Paginator(

        offers,

        10

    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    total_offers = Offer.objects.filter(

        is_deleted=False

    ).count()

    active_offers = Offer.objects.filter(

        is_deleted=False,

        is_active=True,

        start_date__lte=today,

        end_date__gte=today

    ).count()

    expired_offers = Offer.objects.filter(

        is_deleted=False,

        end_date__lt=today

    ).count()

    context = {

        "page_obj": page_obj,

        "search": search,

        "status": status,

        "offer_type": offer_type,

        "total_offers": total_offers,

        "active_offers": active_offers,

        "expired_offers": expired_offers,

    }

    return render(

        request,

        "offer_management.html",

        context

    )



@admin_required
def add_offer(request):

    products = Product.objects.filter(
        is_deleted=False
    )

    categories = Category.objects.filter(
        is_deleted=False
    )

    context = {

        "products": products,

        "categories": categories,

        "form_data": request.POST

    }

    if request.method == "POST":

        try:

            offer_name = request.POST.get(
                "offer_name",
                ""
            ).strip()

            discount_type = request.POST.get(
                "discount_type"
            )

            discount_value = request.POST.get(
                "discount_value"
            )

            min_purchase = request.POST.get(
                "min_purchase"
            ) or 0

            max_discount = request.POST.get(
                "max_discount"
            ) or None

            apply_to = request.POST.get(
                "apply_to"
            )

            start_date = request.POST.get(
                "start_date"
            )

            end_date = request.POST.get(
                "end_date"
            )

            is_active = (
                request.POST.get(
                    "is_active"
                ) == "on"
            )

            if not offer_name:

                messages.error(
                    request,
                    "Offer name is required."
                )

                return render(
                    request,
                    "add_offer.html",
                    context
                )

            if apply_to not in [

                "PRODUCT",

                "CATEGORY"

            ]:

                messages.error(
                    request,
                    "Invalid offer type selected."
                )

                return render(
                    request,
                    "add_offer.html",
                    context
                )

            product_id = None
            category_id = None

            if apply_to == "PRODUCT":

                product_id = request.POST.get(
                    "product"
                )

                if not product_id:

                    messages.error(
                        request,
                        "Please select a product."
                    )

                    return render(
                        request,
                        "add_offer.html",
                        context
                    )

                if not Product.objects.filter(

                    id=product_id,

                    is_deleted=False

                ).exists():

                    messages.error(
                        request,
                        "Selected product does not exist."
                    )

                    return render(
                        request,
                        "add_offer.html",
                        context
                    )

            elif apply_to == "CATEGORY":

                category_id = request.POST.get(
                    "category"
                )

                if not category_id:

                    messages.error(
                        request,
                        "Please select a category."
                    )

                    return render(
                        request,
                        "add_offer.html",
                        context
                    )

                if not Category.objects.filter(

                    id=category_id,

                    is_deleted=False

                ).exists():

                    messages.error(
                        request,
                        "Selected category does not exist."
                    )

                    return render(
                        request,
                        "add_offer.html",
                        context
                    )

            with transaction.atomic():

                offer = Offer.objects.create(

                    offer_name=offer_name,

                    discount_type=discount_type,

                    discount_value=discount_value,

                    min_purchase=min_purchase,

                    max_discount=max_discount,

                    apply_to=apply_to,

                    start_date=start_date,

                    end_date=end_date,

                    is_active=is_active

                )

                if apply_to == "PRODUCT":

                    OfferProduct.objects.create(

                        offer=offer,

                        product_id=product_id

                    )

                else:

                    CategoryOffer.objects.create(

                        offer=offer,

                        category_id=category_id

                    )

            messages.success(

                request,

                "Offer created successfully."

            )

            return redirect(
                "admin_offer:offer_management"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

            return render(
                request,
                "add_offer.html",
                context
            )

    return render(
        request,
        "add_offer.html",
        context
    )


@admin_required
def edit_offer(request, offer_id):

    offer = get_object_or_404(

        Offer,

        id=offer_id,

        is_deleted=False

    )

    products = Product.objects.filter(
        is_deleted=False
    )

    categories = Category.objects.filter(
        is_deleted=False
    )

    if request.method == "POST":

        form_data = request.POST.copy()

    else:

        form_data = {

            "offer_name":
            offer.offer_name,

            "discount_type":
            offer.discount_type,

            "discount_value":
            offer.discount_value,

            "min_purchase":
            offer.min_purchase,

            "max_discount":
            offer.max_discount,

            "apply_to":
            offer.apply_to,

            "start_date": offer.start_date.strftime(
                "%Y-%m-%d"
            ),

            "end_date": offer.end_date.strftime(
                "%Y-%m-%d"
            ),

            "is_active":
            offer.is_active,

        }

        if offer.apply_to == "PRODUCT":

            relation = OfferProduct.objects.filter(

                offer=offer

            ).first()

            if relation:

                form_data["product"] = (
                    relation.product.id
                )

        else:

            relation = CategoryOffer.objects.filter(

                offer=offer

            ).first()

            if relation:

                form_data["category"] = (
                    relation.category.id
                )

    context = {

        "offer": offer,

        "products": products,

        "categories": categories,

        "form_data": form_data

    }

    if request.method == "POST":

        try:

            offer_name = request.POST.get(
                "offer_name",
                ""
            ).strip()

            discount_type = request.POST.get(
                "discount_type"
            )

            discount_value = request.POST.get(
                "discount_value"
            )

            min_purchase = request.POST.get(
                "min_purchase"
            ) or 0

            max_discount = request.POST.get(
                "max_discount"
            ) or None

            apply_to = request.POST.get(
                "apply_to"
            )

            start_date = request.POST.get(
                "start_date"
            )

            end_date = request.POST.get(
                "end_date"
            )

            is_active = (

                request.POST.get(
                    "is_active"
                ) == "on"

            )

            with transaction.atomic():

                offer.offer_name = (
                    offer_name
                )

                offer.discount_type = (
                    discount_type
                )

                offer.discount_value = (
                    discount_value
                )

                offer.min_purchase = (
                    min_purchase
                )

                offer.max_discount = (
                    max_discount
                )

                offer.apply_to = (
                    apply_to
                )

                offer.start_date = (
                    start_date
                )

                offer.end_date = (
                    end_date
                )

                offer.is_active = (
                    is_active
                )

                offer.save()

                OfferProduct.objects.filter(

                    offer=offer

                ).delete()

                CategoryOffer.objects.filter(

                    offer=offer

                ).delete()

                if apply_to == "PRODUCT":

                    product_id = request.POST.get(
                        "product"
                    )

                    if not product_id:

                        raise ValidationError(
                            "Please select a product."
                        )

                    OfferProduct.objects.create(

                        offer=offer,

                        product_id=product_id

                    )

                elif apply_to == "CATEGORY":

                    category_id = request.POST.get(
                        "category"
                    )

                    if not category_id:

                        raise ValidationError(
                            "Please select a category."
                        )

                    CategoryOffer.objects.create(

                        offer=offer,

                        category_id=category_id

                    )

            messages.success(

                request,

                "Offer updated successfully."

            )

            return redirect(
                "admin_offer:offer_management"
            )

        except Exception as e:

            messages.error(
                request,
                str(e)
            )

            return render(
                request,
                "edit_offer.html",
                context
            )

    return render(
        request,
        "edit_offer.html",
        context
    )


from django.shortcuts import (
    get_object_or_404,
    redirect
)
@admin_required
def delete_offer(request, offer_id):

    if request.method == "POST":

        Offer.objects.filter(
            id=offer_id,
            is_deleted=False
        ).update(
            is_deleted=True
        )

        messages.success(
            request,
            "Offer deleted successfully."
        )

    return redirect(
        "admin_offer:offer_management"
    )