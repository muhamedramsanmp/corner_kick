from django.shortcuts import render,redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages

from admin.admin_products.models import Product
from admin.admin_products.models import Variant,Product,ProductImage
from admin.admin_category.models import Category
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem
from .models import Wishlist
from django.http import JsonResponse
from django.db.models import Sum




def shop(request):


    search = request.GET.get(
        "search",
        ""
    ).strip()


    sort = request.GET.get(
        "sort",
        ""
    )

    category_id = request.GET.get(
        "category",
        ""
    )

    min_price = request.GET.get(
        "min_price",
        ""
    )

    max_price = request.GET.get(
        "max_price",
        ""
    )


    products = Product.objects.filter(

        is_deleted=False,

        is_active=True,

        category__is_deleted=False,

        category__is_active=True

    ).prefetch_related(

        "variants__images",

        "category"

    ).order_by("-id")

    if search:

        products = products.filter(

            Q(product_name__icontains=search) |

            Q(description__icontains=search) |

            Q(category__category_name__icontains=search)

        )


    if category_id:

        products = products.filter(
            category_id=category_id
        )

    wishlist_product_ids = []

    if request.user.is_authenticated:

        wishlist_product_ids = Wishlist.objects.filter(
            user=request.user
        ).values_list(
            'product_id',
            flat=True
        )

    filtered_products = []

    for product in products:


        active_variant = product.variants.filter(

            is_deleted=False,

            is_active=True

        ).first()

        # NO ACTIVE VARIANT
        # SKIP PRODUCT

        if not active_variant:
            continue

        variant = product.default_variant


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

        filtered_products.sort(

            key=lambda x:
            x.product_name.lower()

        )

    elif sort == "z-a":

        filtered_products.sort(

            key=lambda x:
            x.product_name.lower(),

            reverse=True

        )

    elif sort == "price-low":

        filtered_products.sort(

            key=lambda x:
            x.default_variant.price
            if x.default_variant else 0

        )

    elif sort == "price-high":

        filtered_products.sort(

            key=lambda x:
            x.default_variant.price
            if x.default_variant else 0,

            reverse=True

        )

    elif sort == "newest":

        filtered_products.sort(

            key=lambda x:
            x.created_at,

            reverse=True

        )

    elif sort == "oldest":

        filtered_products.sort(

            key=lambda x:
            x.created_at

        )

    paginator = Paginator(

        filtered_products,

        6

    )

    page_number = request.GET.get(
        "page"
    )

    products = paginator.get_page(
        page_number
    )

    categories = Category.objects.filter(

        is_deleted=False,

        is_active=True

    ).order_by(

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

        'wishlist_product_ids': wishlist_product_ids,

    }

    return render(

        request,

        "product_filter.html",

        context

    )

def product_details(request, slug):

    product = Product.objects.filter(

        slug=slug,

        is_deleted=False,

        is_active=True,

        category__is_active=True,

        category__is_deleted=False

    ).first()

    if not product:

        messages.error(

            request,

            "Product unavailable"

        )

        return redirect(
            "user_products:shop"
        )

    variants = product.variants.filter(

        is_deleted=False,

        is_active=True

    ).prefetch_related(

        "images"

    )

    default_variant = product.default_variant

    primary_image = None

    if default_variant:

        primary_image = default_variant.images.filter(
            is_primary=True
        ).first()


    related_products_queryset = Product.objects.filter(

        category=product.category,

        is_deleted=False,

        is_active=True

    ).exclude(

        id=product.id

    ).prefetch_related(

        "variants__images"

    )


    page = request.GET.get("related_page")

    paginator = Paginator(

        related_products_queryset,

        8

    )

    related_products = paginator.get_page(page)

    ordered_images = None


    context = {

    "product": product,

    "variants": variants,

    "default_variant": default_variant,

    "primary_image": primary_image,

    "related_products": related_products,


    "is_wishlisted": Wishlist.objects.filter(

        user=request.user,

        product=product

    ).exists() if request.user.is_authenticated else False,

    }
    return render(

        request,

        "product_details.html",

        context

    )

@login_required(login_url='login')
def add_to_cart(request):

    if request.method != "POST":

        return redirect(
            "user_products:shop"
        )

    # =====================================
    # GET DATA
    # =====================================

    variant_id = request.POST.get(
        "variant_id"
    )

    quantity = request.POST.get(
        "quantity",
        1
    )

    # =====================================
    # VALIDATE QUANTITY
    # =====================================

    try:

        quantity = int(quantity)

        if quantity < 1:

            messages.error(
                request,
                "Invalid quantity"
            )

            return redirect(
                "user_products:cart"
            )

    except ValueError:

        messages.error(
            request,
            "Invalid quantity"
        )

        return redirect(
            "user_products:cart"
        )

    # =====================================
    # GET VARIANT
    # =====================================

    variant = Variant.objects.filter(

        id=variant_id,

        is_deleted=False,

        is_active=True,

        product__is_deleted=False,

        product__is_active=True

    ).first()

    if not variant:

        messages.error(
            request,
            "Variant unavailable"
        )

        return redirect(
            "user_products:shop"
        )

    # =====================================
    # OUT OF STOCK
    # =====================================

    if variant.available_stock <= 0:

        messages.error(
            request,
            "Product out of stock"
        )

        return redirect(
            "user_products:cart"
        )

    # =====================================
    # STOCK CHECK
    # =====================================

    if quantity > variant.available_stock:

        messages.error(
            request,
            f"Only {variant.available_stock} items available"
        )

        return redirect(
            "user_products:cart"
        )

    # =====================================
    # GET CART
    # =====================================

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    # =====================================
    # EXISTING CART ITEM
    # =====================================

    cart_item = CartItem.objects.filter(
        cart=cart,
        variant=variant
    ).first()

    # =====================================
    # UPDATE EXISTING ITEM
    # =====================================

    if cart_item:

        new_quantity = (
            cart_item.quantity + quantity
        )

        # MAXIMUM 5 LIMIT

        if new_quantity > 5:

            messages.error(
                request,
                "Maximum 5 quantities allowed per product"
            )

            return redirect(
                "user_products:cart"
            )

        # STOCK CHECK

        if new_quantity > variant.available_stock:

            messages.error(
                request,
                f"Only {variant.available_stock} items available"
            )

            return redirect(
                "user_products:cart"
            )

        cart_item.quantity = new_quantity

        cart_item.save()

        messages.success(
            request,
            "Cart quantity updated"
        )

    # =====================================
    # NEW CART ITEM
    # =====================================

    else:

        # MAXIMUM 5 LIMIT

        if quantity > 5:

            messages.error(
                request,
                "Maximum 5 quantities allowed per product"
            )

            return redirect(
                "user_products:cart"
            )

        CartItem.objects.create(

            cart=cart,

            variant=variant,

            quantity=quantity

        )

        cart_count = CartItem.objects.filter(
            cart__user=request.user
        ).count()

        return JsonResponse({

            "success": True,

            "message": "Product added to cart",

            "cart_count": cart_count

        })


@login_required(login_url='login')
def cart(request):


    cart = Cart.objects.filter(

        user=request.user

    ).first()


    if not cart:

        context = {

            "cart_items": [],

            "subtotal": 0,

            "shipping": 0,

            "total": 0,

        }

        return render(

            request,

            "cart.html",

            context

        )


    cart_items = CartItem.objects.filter(

        cart=cart

    ).select_related(

        "variant",
        "variant__product"

    ).prefetch_related(

        "variant__images"

    )


    subtotal = 0

    shipping = 0

    total = 0

    for item in cart_items:

        item.subtotal = (

            item.variant.price *

            item.quantity

        )

        subtotal += item.subtotal

    # SHIPPING

    if subtotal > 0:

        shipping = 99

    total = subtotal + shipping



    context = {

        "cart_items": cart_items,

        "subtotal": subtotal,

        "shipping": shipping,

        "total": total,

    }

    return render(

        request,

        "cart.html",

        context

    )

@login_required(login_url='login')
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

    action = request.GET.get("action")

    # =========================
    # INCREASE
    # =========================

    if action == "increase":

        if cart_item.quantity >= 5:

            return JsonResponse({

                "success": False,

                "message": "Maximum 5 quantities allowed",

                "quantity": cart_item.quantity,

                "subtotal":cart_item.variant.price * cart_item.quantity,

                "cart_total":cart_item.cart.total_price

            })

        total_reserved = CartItem.objects.filter(

            variant=cart_item.variant

        ).exclude(

            id=cart_item.id

        ).aggregate(

            total=Sum("quantity")

        )["total"] or 0

        remaining_stock = (

            cart_item.variant.stock - total_reserved

        )

        if cart_item.quantity + 1 > remaining_stock:

            return JsonResponse({

                "success": False,

                "message": f"Only {remaining_stock} items available",

                "quantity": cart_item.quantity,

                "subtotal":cart_item.variant.price * cart_item.quantity,

                "cart_total":cart_item.cart.total_price

            })

        cart_item.quantity += 1

        cart_item.save()

        message = "Quantity increased"

    # =========================
    # DECREASE
    # =========================

    elif action == "decrease":

        if cart_item.quantity <= 1:

            cart_item.delete()

            return JsonResponse({

                "success": True,

                "removed": True,

                "message": "Product removed from cart",

                "cart_count": CartItem.objects.filter(
                    cart__user=request.user
                ).count()

            })

        cart_item.quantity -= 1

        cart_item.save()

        message = "Quantity decreased"

    cart_count = CartItem.objects.filter(
        cart__user=request.user
    ).count()

    return JsonResponse({

        "success": True,

        "message": message,

        "quantity": cart_item.quantity,

        "subtotal": cart_item.variant.price * cart_item.quantity,

        "cart_total": cart_item.cart.total_price,

        "cart_count": cart_count

    })


@login_required(login_url='login')
def remove_cart_item(request, item_id):


    cart_item = CartItem.objects.filter(

        id=item_id,

        cart__user=request.user

    ).first()


    if not cart_item:

        messages.error(

            request,

            "Cart item not found"

        )

        return redirect(
            'user_products:cart'
        )


    cart_item.delete()


    cart_count = CartItem.objects.filter(
    cart__user=request.user
    ).count()

    wishlist_count = Wishlist.objects.filter(
        user=request.user
    ).count()

    return JsonResponse({

        "success": True,

        "message": "Product moved to cart",

        "cart_count": cart_count,

        "wishlist_count": wishlist_count

    })

 



@login_required(login_url='login')
def toggle_wishlist(request, product_id):


    product = Product.objects.filter(

        id=product_id,

        is_deleted=False,

        is_active=True

    ).first()

    # =====================================
    # INVALID PRODUCT
    # =====================================

    if not product:

        return JsonResponse({

            "success": True,

            "action": action,

            "message": message,

            "wishlist_count": wishlist_count

        })

    # =====================================
    # EXISTING WISHLIST
    # =====================================

    wishlist_item = Wishlist.objects.filter(

        user=request.user,

        product=product

    ).first()

    # =====================================
    # REMOVE WISHLIST
    # =====================================

    if wishlist_item:

        wishlist_item.delete()

        action = "removed"

        message = "Removed from wishlist"


    else:

        Wishlist.objects.create(

            user=request.user,

            product=product

        )

        action = "added"

        message = "Added to wishlist"


    wishlist_count = Wishlist.objects.filter(

        user=request.user

    ).count()

    return JsonResponse({

        "success": True,

        "action": action,

        "message": message,

        "wishlist_count": wishlist_count

    })

from django.db.models import Sum


@login_required(login_url='login')
def wishlist_page(request):

    wishlist_items = Wishlist.objects.filter(

        user=request.user,

        product__is_deleted=False,

        product__is_active=True

    ).select_related(

        'product',

        'product__category'

    ).prefetch_related(

        'product__variants__images'

    ).order_by(

        '-created_at'

    )

    context = {

        'wishlist_items': wishlist_items

    }

    return render(

        request,

        'wishlist.html',

        context

    )


@login_required(login_url='login')
def wishlist_to_cart(request, product_id):

    # =====================================
    # GET PRODUCT
    # =====================================

    product = Product.objects.filter(

        id=product_id,

        is_deleted=False,

        is_active=True

    ).first()

    if not product:

        messages.error(

            request,

            "Product unavailable"

        )

        return redirect(
            "user_products:wishlist"
        )

    # =====================================
    # GET VARIANT
    # =====================================

    variant = product.default_variant

    if not variant:

        messages.error(

            request,

            "Variant unavailable"

        )

        return redirect(
            "user_products:wishlist"
        )

    # =====================================
    # OUT OF STOCK
    # =====================================

    if variant.available_stock <= 0:

        messages.error(

            request,

            "Product out of stock"

        )

        return redirect(
            "user_products:wishlist"
        )

    # =====================================
    # GET CART
    # =====================================

    cart, created = Cart.objects.get_or_create(

        user=request.user

    )

    # =====================================
    # EXISTING CART ITEM
    # =====================================

    cart_item = CartItem.objects.filter(

        cart=cart,

        variant=variant

    ).first()

    # =====================================
    # UPDATE EXISTING ITEM
    # =====================================

    if cart_item:

        # MAXIMUM 5 LIMIT

        if cart_item.quantity >= 5:

            messages.error(

                request,

                "Maximum 5 quantities allowed"

            )

            return redirect(
                "user_products:wishlist"
            )

        # RESERVED STOCK BY OTHER USERS

        total_reserved = CartItem.objects.filter(
            variant=variant
        ).exclude(
            id=cart_item.id
        ).aggregate(
            total=Sum("quantity")
        )["total"] or 0

        remaining_stock = (
            variant.stock - total_reserved
        )

        # STOCK CHECK

        if cart_item.quantity + 1 > remaining_stock:

            messages.error(

                request,

                f"Only {remaining_stock} items available"

            )

            return redirect(
                "user_products:wishlist"
            )

        cart_item.quantity += 1

        cart_item.save()

    # =====================================
    # CREATE NEW CART ITEM
    # =====================================

    else:

        CartItem.objects.create(

            cart=cart,

            variant=variant,

            quantity=1

        )

    # =====================================
    # REMOVE FROM WISHLIST
    # =====================================

    Wishlist.objects.filter(

        user=request.user,

        product=product

    ).delete()

    # =====================================
    # COUNTS
    # =====================================

    cart_count = CartItem.objects.filter(

        cart__user=request.user

    ).count()

    wishlist_count = Wishlist.objects.filter(

        user=request.user

    ).count()

    # =====================================
    # AJAX RESPONSE
    # =====================================

    return JsonResponse({

        "success": True,

        "message": "Product moved to cart",

        "cart_count": cart_count,

        "wishlist_count": wishlist_count

    })

    