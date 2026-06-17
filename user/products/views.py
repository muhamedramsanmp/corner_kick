from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib import messages

from admin.admin_products.models import Product
from admin.admin_products.models import Variant, Product, ProductImage
from admin.admin_category.models import Category
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem
from .models import Wishlist
from django.http import JsonResponse
from django.db.models import Sum
from user.decorators import user_required
from admin.admin_offer.utils import calculate_discounted_price
import json
from .utils import remove_invalid_cart_items
from user.products.models import Review
from user.user_orders.models import OrderItem

def shop(request):

    search = request.GET.get("search", "").strip()

    sort = request.GET.get("sort", "")

    category_id = request.GET.get("category", "")

    min_price = request.GET.get("min_price", "")

    max_price = request.GET.get("max_price", "")

    products = (
        Product.objects.filter(
            is_deleted=False,
            is_active=True,
            category__is_deleted=False,
            category__is_active=True,
        )
        .prefetch_related("variants__images", "category")
        .order_by("-id")
    )

    if search:

        products = products.filter(
            Q(product_name__icontains=search)
            | Q(description__icontains=search)
            | Q(category__category_name__icontains=search)
        )

    if category_id:

        products = products.filter(category_id=category_id)

    wishlist_product_ids = []

    if request.user.is_authenticated:

        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list(
            "product_id", flat=True
        )

    filtered_products = []

    for product in products:

        active_variant = product.variants.filter(
            is_deleted=False, is_active=True
        ).first()

        if not active_variant:
            continue

        variant = product.default_variant

        if variant:

            product.price_data = calculate_discounted_price(variant)

        else:

            product.price_data = None

        if min_price and variant:

            try:

                if variant.price < float(min_price):
                    continue

            except:
                pass

        if max_price and variant:

            try:

                if variant.price > float(max_price):
                    continue

            except:
                pass

        filtered_products.append(product)

    if sort == "a-z":

        filtered_products.sort(key=lambda x: x.product_name.lower())

    elif sort == "z-a":

        filtered_products.sort(key=lambda x: x.product_name.lower(), reverse=True)

    elif sort == "price-low":

        filtered_products.sort(
            key=lambda x: x.default_variant.price if x.default_variant else 0
        )

    elif sort == "price-high":

        filtered_products.sort(
            key=lambda x: x.default_variant.price if x.default_variant else 0,
            reverse=True,
        )

    elif sort == "newest":

        filtered_products.sort(key=lambda x: x.created_at, reverse=True)

    elif sort == "oldest":

        filtered_products.sort(key=lambda x: x.created_at)

    paginator = Paginator(filtered_products, 9)

    page_number = request.GET.get("page")

    products = paginator.get_page(page_number)

    categories = Category.objects.filter(is_deleted=False, is_active=True).order_by(
        "category_name"
    )

    context = {
        "products": products,
        "categories": categories,
        "search": search,
        "sort": sort,
        "category_id": category_id,
        "min_price": min_price,
        "max_price": max_price,
        "wishlist_product_ids": wishlist_product_ids,
    }

    return render(request, "product_filter.html", context)


def product_details(request, slug):

    product = Product.objects.filter(
        slug=slug,
        is_deleted=False,
        is_active=True,
        category__is_active=True,
        category__is_deleted=False,
    ).first()

    if not product:

        messages.error(request, "Product unavailable")

        return redirect("user_products:shop")

    variants = product.variants.filter(
        is_deleted=False, is_active=True
    ).prefetch_related("images")
    variant_offer_data = {}

    for variant in variants:

        offer_data = calculate_discounted_price(variant)

        variant_offer_data[str(variant.id)] = {
            "original_price": str(offer_data["original_price"]),
            "final_price": str(offer_data["final_price"]),
            "discount_amount": str(offer_data["discount_amount"]),
            "offer_name": (
                offer_data["offer"].offer_name if offer_data["offer"] else ""
            ),
            "discount_type": (
                offer_data["offer"].discount_type if offer_data["offer"] else ""
            ),
            "discount_value": (
                str(offer_data["offer"].discount_value) if offer_data["offer"] else ""
            ),
        }

    default_variant = product.default_variant

    price_data = None

    if default_variant:

        price_data = calculate_discounted_price(default_variant)

    primary_image = None

    if default_variant:

        primary_image = default_variant.images.filter(is_primary=True).first()

    related_products_queryset = (
        Product.objects.filter(
            category=product.category, is_deleted=False, is_active=True
        )
        .exclude(id=product.id)
        .prefetch_related("variants__images")
    )

    page = request.GET.get("related_page")

    paginator = Paginator(related_products_queryset, 8)

    related_products = paginator.get_page(page)

    ordered_images = None

    approved_reviews = product.reviews.filter(
        status="approved"
    ).select_related("user")
    user_pending_review = None

    if request.user.is_authenticated:

        user_pending_review = product.reviews.filter(
            user=request.user
        ).exclude(
            status="approved"
        ).first()
    user_review = None

    if request.user.is_authenticated:

        user_review = product.reviews.filter(
            user=request.user
        ).first()

    context = {
        "product": product,
        "variants": variants,
        "default_variant": default_variant,
        "price_data": price_data,
        "primary_image": primary_image,
        "related_products": related_products,
        "variant_offer_data": variant_offer_data,
        "approved_reviews": approved_reviews,
        "can_review": product.can_user_review(request.user)
        if request.user.is_authenticated
        else False,   
        "is_wishlisted": (
            Wishlist.objects.filter(user=request.user, product=product).exists()
            if request.user.is_authenticated
            else False
        ),
        "user_review": user_review,
        "user_pending_review": user_pending_review,
    }
    return render(request, "product_details.html", context)



@login_required(login_url="login")
def add_review(request, product_id):

    if request.method != "POST":
        return redirect("user_products:shop")

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True,
        is_deleted=False,
    )

    rating = request.POST.get("rating")
    review_text = request.POST.get("review_text", "").strip()

    if not rating:
        messages.error(request, "Please select a rating.")
        return redirect(
            "user_products:product_details",
            slug=product.slug
        )

    existing_review = Review.objects.filter(
        user=request.user,
        product=product,
    ).first()

    if not existing_review and not product.can_user_review(request.user):

        messages.error(
            request,
            "You cannot review this product."
        )

        return redirect(
            "user_products:product_details",
            slug=product.slug
        )
    
    order_item = OrderItem.objects.filter(
        order__user=request.user,
        order__order_status="Delivered",
        product=product,
    ).order_by("-id").first()
    if existing_review:

        existing_review.rating = int(rating)

        existing_review.review_text = review_text

        existing_review.status = "pending"

        existing_review.save()

    else:

        Review.objects.create(
            user=request.user,
            product=product,
            order=order_item.order,
            rating=int(rating),
            review_text=review_text,
            status="pending",
        )

        messages.success(
            request,
            "Review submitted successfully and awaiting approval."
        )


    return redirect(
        "user_products:product_details",
        slug=product.slug
    )

@login_required
def delete_review(request, review_id):

    review = get_object_or_404(
        Review,
        id=review_id,
        user=request.user
    )

    product_slug = review.product.slug

    review.delete()

    messages.success(
        request,
        "Review deleted successfully."
    )

    return redirect(
        "user_products:product_details",
        slug=product_slug
    )

@login_required(login_url="login")
def add_to_cart(request):

    if request.method != "POST":

        return redirect("user_products:shop")

    variant_id = request.POST.get("variant_id")

    quantity = request.POST.get("quantity", 1)

    try:

        quantity = int(quantity)

        if quantity < 1:

            messages.error(request, "Invalid quantity")

            return redirect("user_products:cart")

    except ValueError:

        messages.error(request, "Invalid quantity")

        return redirect("user_products:cart")

    variant = Variant.objects.filter(
        id=variant_id,
        is_deleted=False,
        is_active=True,
        product__is_deleted=False,
        product__is_active=True,
    ).first()

    if not variant:

        messages.error(request, "Variant unavailable")

        return redirect("user_products:shop")

    if variant.available_stock <= 0:

        messages.error(request, "Product out of stock")

        return redirect("user_products:cart")

    if quantity > variant.available_stock:

        messages.error(request, f"Only {variant.available_stock} items available")

        return redirect("user_products:cart")

    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item = CartItem.objects.filter(cart=cart, variant=variant).first()

    if cart_item:

        new_quantity = cart_item.quantity + quantity

        if new_quantity > 5:

            messages.error(request, "Maximum 5 quantities allowed per product")

            return redirect("user_products:cart")

        if new_quantity > variant.available_stock:

            messages.error(request, f"Only {variant.available_stock} items available")

            return redirect("user_products:cart")

        cart_item.quantity = new_quantity

        cart_item.save()

        messages.success(request, "Cart quantity updated")

    else:

        if quantity > 5:

            messages.error(request, "Maximum 5 quantities allowed per product")

            return redirect("user_products:cart")

        cart_item = CartItem.objects.create(
            cart=cart, variant=variant, quantity=quantity
        )

    cart_items = CartItem.objects.filter(cart=cart)

    cart_total = 0

    for item in cart_items:

        price_data = calculate_discounted_price(item.variant)

        cart_total += price_data["final_price"] * item.quantity

        cart_count = cart_items.count()

        price_data = calculate_discounted_price(cart_item.variant)

        subtotal = price_data["final_price"] * cart_item.quantity

    return JsonResponse(
        {
            "success": True,
            "message": "Product added to cart",
            "cart_count": cart_count,
            "subtotal": subtotal,
            "cart_total": cart_total,
            "quantity": cart_item.quantity,
        }
    )


@user_required
def cart(request):

    cart = Cart.objects.filter(user=request.user).first()

    if not cart:

        context = {
            "cart_items": [],
            "subtotal": 0,
            "shipping": 0,
            "total": 0,
        }

        return render(request, "cart.html", context)

    remove_invalid_cart_items(cart)

    cart_items = (
        CartItem.objects.filter(
            cart=cart,
            variant__is_active=True,
            variant__product__is_active=True,
            variant__product__category__is_active=True,
        )
        .select_related("variant", "variant__product", "variant__product__category")
        .prefetch_related("variant__images")
    )

    subtotal = 0
    shipping = 0
    total = 0

    subtotal = 0
    total_discount = 0

    for item in cart_items:

        item.price_data = calculate_discounted_price(item.variant)

        original_total = item.price_data["original_price"] * item.quantity

        final_total = item.price_data["final_price"] * item.quantity

        item.subtotal = final_total

        item.discount_total = original_total - final_total

        subtotal += original_total

        total_discount += item.discount_total

    total = subtotal - total_discount

    context = {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "total_discount": total_discount,
        "shipping": shipping,
        "total": total,
    }

    return render(request, "cart.html", context)


@login_required(login_url="login")
def update_cart_quantity(request, item_id):
    cart_item = CartItem.objects.filter(
        id=item_id,
        cart__user=request.user
    ).first()

    if not cart_item:

        return JsonResponse({
            "success": False,
            "message": "Cart item not found"
        })

    remove_invalid_cart_items(
        cart_item.cart
    )

    cart_item = CartItem.objects.filter(
        id=item_id,
        cart__user=request.user
    ).first()

    if not cart_item:

        return JsonResponse({
            "success": False,
            "removed": True,
            "message": "Product is no longer available"
        })

    price_data = calculate_discounted_price(cart_item.variant)

    final_price = price_data["final_price"]

    # Current cart total (for validation responses)

    cart_total = 0

    for item in cart_item.cart.items.all():

        item_price_data = calculate_discounted_price(item.variant)

        cart_total += item_price_data["final_price"] * item.quantity

    action = request.GET.get("action")

    if action == "increase":

        if cart_item.quantity >= 5:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Maximum 5 quantities allowed",
                    "quantity": cart_item.quantity,
                    "subtotal": final_price * cart_item.quantity,
                    "stock": cart_item.variant.available_stock,
                    "cart_total": cart_total,
                    "cart_count": CartItem.objects.filter(
                        cart__user=request.user
                    ).count(),
                }
            )

        total_reserved = (
            CartItem.objects.filter(variant=cart_item.variant)
            .exclude(id=cart_item.id)
            .aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        remaining_stock = cart_item.variant.stock - total_reserved

        if cart_item.quantity + 1 > remaining_stock:

            return JsonResponse(
                {
                    "success": False,
                    "message": f"Only {remaining_stock} items available",
                    "quantity": cart_item.quantity,
                    "subtotal": final_price * cart_item.quantity,
                    "stock": cart_item.variant.available_stock,
                    "cart_total": cart_total,
                }
            )

        cart_item.quantity += 1

        cart_item.save()

        message = "Quantity increased"

    elif action == "decrease":

        if cart_item.quantity <= 1:
            # cart_item.delete()

            return JsonResponse(
                {
                    "success": False,
                    "message": "Minimum quantity is 1",
                    "quantity": cart_item.quantity,
                    "subtotal": final_price * cart_item.quantity,
                    "stock": cart_item.variant.available_stock,
                    "cart_total": cart_total,
                    "cart_count": CartItem.objects.filter(
                        cart__user=request.user
                    ).count(),
                }
            )

        cart_item.quantity -= 1

        cart_item.save()

        message = "Quantity decreased"

    else:

        return JsonResponse({"success": False, "message": "Invalid action"})

    # Recalculate totals AFTER update

    subtotal = 0
    total_discount = 0

    for item in cart_item.cart.items.all():

        item_price_data = calculate_discounted_price(item.variant)

        original_total = item_price_data["original_price"] * item.quantity

        subtotal += original_total

        total_discount += item_price_data["discount_amount"] * item.quantity

    total = subtotal - total_discount

    cart_count = (
        CartItem.objects.filter(
            cart__user=request.user
        ).aggregate(
            total=Sum("quantity")
        )["total"]
        or 0
    )

    return JsonResponse(
        {
            "success": True,
            "message": message,
            "quantity": cart_item.quantity,
            "subtotal": final_price * cart_item.quantity,
            "summary_subtotal": subtotal,
            "discount": total_discount,
            "total": total,
            "stock": cart_item.variant.available_stock,
            "cart_count": cart_count,
        }
    )


@login_required(login_url="login")
def remove_cart_item(request, item_id):

    cart_item = CartItem.objects.filter(id=item_id, cart__user=request.user).first()

    if not cart_item:

        messages.error(request, "Cart item not found")

        return redirect("user_products:cart")

    cart = cart_item.cart
    cart_item.delete()

    subtotal = 0
    total_discount = 0

    remaining_items = CartItem.objects.filter(cart=cart)

    for item in remaining_items:

        price_data = calculate_discounted_price(item.variant)

        original_total = price_data["original_price"] * item.quantity

        subtotal += original_total

        total_discount += (
            price_data["discount_amount"] * item.quantity
        )

    total = subtotal - total_discount

    cart_count = CartItem.objects.filter(cart__user=request.user).count()

    wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return JsonResponse(
        {
            "success": True,
            "message": "Product removed from cart",
            "cart_count": cart_count,
            "wishlist_count": wishlist_count,
            "subtotal": subtotal,
            "discount": total_discount,
            "total": total,
        }
    )


@login_required(login_url="login")
def toggle_wishlist(request, product_id):

    product = Product.objects.filter(
        id=product_id, is_deleted=False, is_active=True
    ).first()

    if not product:

        return JsonResponse(
            {
                "success": True,
                "action": action,
                "message": message,
                "wishlist_count": wishlist_count,
            }
        )

    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()

    if wishlist_item:

        wishlist_item.delete()

        action = "removed"

        message = "Removed from wishlist"

    else:

        Wishlist.objects.create(user=request.user, product=product)

        action = "added"

        message = "Added to wishlist"

    wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return JsonResponse(
        {
            "success": True,
            "action": action,
            "message": message,
            "wishlist_count": wishlist_count,
        }
    )


@user_required
def wishlist_page(request):

    sort = request.GET.get("sort", "")

    # Remove wishlist items whose product/category is inactive
    Wishlist.objects.filter(user=request.user).filter(
        Q(product__is_deleted=True)
        | Q(product__is_active=False)
        | Q(product__category__is_active=False)
    ).delete()

    # Remove wishlist items whose product has no active variants
    Wishlist.objects.filter(user=request.user).annotate(
        active_variants=Count(
            "product__variants", filter=Q(product__variants__is_active=True)
        )
    ).filter(active_variants=0).delete()

    wishlist_items = (
        Wishlist.objects.filter(
            user=request.user,
            product__is_deleted=False,
            product__is_active=True,
            product__category__is_active=True,
            product__variants__is_active=True,
        )
        .select_related("product", "product__category")
        .prefetch_related("product__variants__images")
        .distinct()
    )

    Wishlist.objects.filter(product__is_active=False).delete()

    if sort == "price_low":

        wishlist_items = wishlist_items.order_by("product__variants__price")

    elif sort == "price_high":

        wishlist_items = wishlist_items.order_by("-product__variants__price")

    elif sort == "a_z":

        wishlist_items = wishlist_items.order_by("product__product_name")

    elif sort == "z_a":

        wishlist_items = wishlist_items.order_by("-product__product_name")

    else:

        wishlist_items = wishlist_items.order_by("-created_at")

    paginator = Paginator(wishlist_items, 6)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)
    for item in page_obj:

        product = item.product

        variant = product.default_variant

        if variant:

            product.price_data = calculate_discounted_price(variant)

    context = {
        "wishlist_items": page_obj,
        "page_obj": page_obj,
        "sort": sort,
    }

    return render(request, "wishlist.html", context)


@login_required(login_url="login")
def wishlist_to_cart(request, product_id):

    product = Product.objects.filter(
        id=product_id, is_deleted=False, is_active=True
    ).first()

    if not product:

        messages.error(request, "Product unavailable")

        return redirect("user_products:wishlist")

    variant = product.default_variant

    if not variant:

        messages.error(request, "Variant unavailable")

        return redirect("user_products:wishlist")

    if variant.available_stock <= 0:

        messages.error(request, "Product out of stock")

        return redirect("user_products:wishlist")

    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item = CartItem.objects.filter(cart=cart, variant=variant).first()

    if cart_item:

        if cart_item.quantity >= 5:

            messages.error(request, "Maximum 5 quantities allowed")

            return redirect("user_products:wishlist")

        total_reserved = (
            CartItem.objects.filter(variant=variant)
            .exclude(id=cart_item.id)
            .aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        remaining_stock = variant.stock - total_reserved

        if cart_item.quantity + 1 > remaining_stock:

            messages.error(request, f"Only {remaining_stock} items available")

            return redirect("user_products:wishlist")

        cart_item.quantity += 1

        cart_item.save()

    else:

        CartItem.objects.create(cart=cart, variant=variant, quantity=1)
    Wishlist.objects.filter(user=request.user, product=product).delete()

    cart_count = CartItem.objects.filter(cart__user=request.user).count()

    wishlist_count = Wishlist.objects.filter(user=request.user).count()

    return JsonResponse(
        {
            "success": True,
            "message": "Product moved to cart",
            "cart_count": cart_count,
            "wishlist_count": wishlist_count,
        }
    )

