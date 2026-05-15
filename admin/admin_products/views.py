# admin_products/views.py

from django.shortcuts import render,redirect,get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from .models import Product,Variant,ProductImage
from admin.admin_category.models import Category
from django.contrib import messages
from .models import Product,Variant,ProductImage,Category  
from django.views.decorators.cache import never_cache 


@never_cache
@login_required(login_url='login')
def product_management(request):

    search = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', '')


    products = Product.objects.filter(
        is_deleted=False,
        category__is_deleted=False
    ).select_related(
        'category'
    ).prefetch_related(
        'variants__images'
    )

    if search:

        products = products.filter(

            Q(product_name__icontains=search) |
            Q(category__category_name__icontains=search) |
            Q(variants__sku__icontains=search)

        ).distinct()


    if category_id:

        products = products.filter(
            category_id=category_id
        )


    if status == 'active':

        products = products.filter(
            is_active=True
        )

    elif status == 'inactive':

        products = products.filter(
            is_active=False
        )

    paginator = Paginator(products, 5)

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(page_number)


    categories = Category.objects.filter(
        is_deleted=False,
        is_active=True
    )

    total_products = Product.objects.filter(
        is_deleted=False
    ).count()

    active_products = Product.objects.filter(
        is_deleted=False,
        is_active=True
    ).count()

    out_of_stock = Product.objects.filter(
        variants__stock=0,
        is_deleted=False
    ).distinct().count()

    new_products = Product.objects.filter(
        is_deleted=False
    ).order_by('-created_at')[:10].count()

    context = {

        'page_obj': page_obj,
        'categories': categories,

        'search': search,
        'category_id': category_id,
        'status': status,

        'total_products': total_products,
        'active_products': active_products,
        'out_of_stock': out_of_stock,
        'new_products': new_products,

    }

    return render(
        request,
        'product_management.html',
        context
    )

@login_required(login_url='login')
def add_product(request):

    categories = Category.objects.filter(is_active=True,is_deleted=False)

    if request.method == "POST":

        product_name = request.POST.get("product_name")
        description = request.POST.get("description")
        category_id = request.POST.get("category")

        description_fit = request.POST.get("description_fit")
        materials = request.POST.get("materials")
        care_guide = request.POST.get("care_guide")
        delivery_returns = request.POST.get("delivery_returns")

        is_active = True if request.POST.get("is_active") else False

        try:

            category = Category.objects.get(id=category_id)

        except Category.DoesNotExist:

            messages.error(request, "Invalid category")
            return redirect("add_product")

        Product.objects.create(

            product_name=product_name,

            description=description,

            description_fit=description_fit,

            materials=materials,

            care_guide=care_guide,

            delivery_returns=delivery_returns,

            category=category,

            is_active=is_active,

        )

        messages.success(request, "Product added successfully")

        return redirect("admin_products:product_management")

    return render(
        request,
        "add_product.html",
        {
            "categories": categories,
        }
    )

@login_required(login_url='login')
def edit_product(request, product_id):

    product = get_object_or_404(

        Product,

        id=product_id,

        is_deleted=False

    )

    categories = Category.objects.filter(

        is_active=True,
        is_deleted=False

    )

    if request.method == "POST":

        # ================= PRODUCT =================

        product.product_name = request.POST.get(
            "product_name"
        )

        product.description = request.POST.get(
            "description"
        )

        product.description_fit = request.POST.get(
            "description_fit"
        )

        product.materials = request.POST.get(
            "materials"
        )

        product.care_guide = request.POST.get(
            "care_guide"
        )

        product.delivery_returns = request.POST.get(
            "delivery_returns"
        )

        category_id = request.POST.get(
            "category"
        )

        product.is_active = (
            True if request.POST.get("is_active")
            else False
        )

        # ================= CATEGORY =================

        try:

            category = Category.objects.get(
                id=category_id
            )

            product.category = category

        except Category.DoesNotExist:

            messages.error(
                request,
                "Invalid category"
            )

            return redirect(
                "edit_product",
                product_id=product.id
            )


        product.save()

        messages.success(

            request,

            "Product updated successfully"

        )

        return redirect(

            "admin_products:product_management"

        )

    return render(

        request,

        "edit_product.html",

        {

            "product": product,

            "categories": categories,

        }

    )

@never_cache
@login_required(login_url='login')
def delete_product(request, product_id):

    product = Product.objects.filter(
        id=product_id
    ).first()

    if not product or product.is_deleted:

        messages.error(
            request,
            "Product already deleted"
        )

        return redirect(
            "admin_products:product_management"
        )


    if request.method == "POST":


        product.delete()

        messages.success(
            request,
            "Product deleted successfully"
        )

        return redirect(
            "admin_products:product_management"
        )


    return render(

        request,

        "delete_product.html",

        {
            "product": product
        }

    )


@never_cache
@login_required(login_url='login')
def variant_management(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        is_deleted=False
    )

    variants = Variant.objects.filter(
        product=product,
        is_deleted=False
    ).order_by('-created_at')

    # SEARCH

    search = request.GET.get("search")

    if search:

        variants = variants.filter(
            sku__icontains=search
        )

    # PAGINATION

    paginator = Paginator(variants, 5)

    page_number = request.GET.get('page')

    page_obj = paginator.get_page(page_number)

    # STATS

    total_stock = sum(
        variant.stock
        for variant in variants
    )

    active_variants = variants.filter(
        is_active=True
    ).count()

    low_stock = variants.filter(
        stock__lt=20
    ).count()

    default_variant = variants.filter(
        is_default=True
    ).first()


    return render(

        request,

        "variant_management.html",

        {

            "product": product,

            "page_obj": page_obj,

            "total_stock": total_stock,

            "active_variants": active_variants,

            "low_stock": low_stock,

            "default_variant": default_variant,

        }

    )
@login_required(login_url='login')
def add_variant(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        is_deleted=False
    )

    if request.method == "POST":

        color = request.POST.get("color", "").strip()

        size = request.POST.get("size", "").strip()

        sku = request.POST.get("sku", "").strip()

        stock = request.POST.get("stock", "").strip()

        price = request.POST.get("price", "").strip()

        is_default = True if request.POST.get("is_default") else False

        is_active = True if request.POST.get("is_active") else False


        # 🔥 COMMON CONTEXT
        context = {
            "product": product,
            "form_data": request.POST
        }


        # ================= VALIDATIONS =================

        if not color:

            messages.error(
                request,
                "Color is required",
                extra_tags="variant"
            )

            return render(request, "add_variant.html", context)


        if not size:

            messages.error(
                request,
                "Size is required",
                extra_tags="variant"
            )

            return render(request, "add_variant.html", context)


        if not sku:

            messages.error(
                request,
                "SKU is required",
                extra_tags="variant"
            )

            return render(request, "add_variant.html", context)


        if Variant.objects.filter(
            sku=sku,
            is_deleted=False
        ).exists():

            messages.error(
                request,
                "SKU already exists",
                extra_tags="variant"
            )

            return render(request, "add_variant.html", context)


        # ================= STOCK =================

        try:

            stock = int(stock)

            if stock < 0:

                messages.error(
                    request,
                    "Stock cannot be negative",
                    extra_tags="variant"
                )

                return render(request, "add_variant.html", context)

        except ValueError:

            messages.error(
                request,
                "Invalid stock value",
                extra_tags="variant"
            )

            return render(request, "add_variant.html", context)


        # ================= PRICE =================

        try:

            price = float(price)

            if price < 0:

                messages.error(
                    request,
                    "Price cannot be negative",
                    extra_tags="variant"
                )

                return render(request, "add_variant.html", context)

        except ValueError:

            messages.error(
                request,
                "Invalid price value",
                extra_tags="variant"
            )

            return render(request, "add_variant.html", context)


        # ================= IMAGES =================

        images = request.FILES.getlist("images")

        valid_images = [
            image for image in images
            if image and image.name
        ]


        if len(valid_images) < 3:

            messages.error(
                request,
                "Minimum 3 images are required",
                extra_tags="variant"
            )

            return render(request, "add_variant.html", context)


        if len(valid_images) > 4:

            messages.error(
                request,
                "Maximum 4 images allowed",
                extra_tags="variant"
            )

            return render(request, "add_variant.html", context)


        # ================= DUPLICATE VARIANT =================

        if Variant.objects.filter(
            product=product,
            color=color,
            size=size,
            is_deleted=False
        ).exists():

            messages.error(
                request,
                "This variant already exists",
                extra_tags="variant"
            )

            return render(request, "add_variant.html", context)


        # ================= DEFAULT =================

        if is_default:

            Variant.objects.filter(
                product=product
            ).update(
                is_default=False
            )


        # ================= CREATE VARIANT =================

        variant = Variant.objects.create(

            product=product,

            sku=sku,

            color=color,

            size=size,

            stock=stock,

            price=price,

            is_active=is_active,

            is_default=is_default
        )


        # ================= SAVE IMAGES =================

        for index, image in enumerate(valid_images):

            ProductImage.objects.create(

                variant=variant,

                image=image,

                is_primary=True if index == 0 else False

            )


        messages.success(
            request,
            "Variant added successfully"
        )

        return redirect(
            "admin_products:variant_management",
            product_id=product.id
        )


    return render(
        request,
        "add_variant.html",
        {
            "product": product
        }
    )

@login_required(login_url='login')
def edit_variant(request, variant_id):

    variant = get_object_or_404(

        Variant,

        id=variant_id,

        is_deleted=False

    )

    product = variant.product

    # =========================================
    # EDIT VARIANT
    # =========================================

    if request.method == "POST":

        color = request.POST.get(
            "color",
            ""
        ).strip()

        size = request.POST.get(
            "size",
            ""
        ).strip()

        sku = request.POST.get(
            "sku",
            ""
        ).strip()

        stock = request.POST.get(
            "stock",
            ""
        ).strip()

        price = request.POST.get(
            "price",
            ""
        ).strip()

        is_active = (
            True if request.POST.get("is_active")
            else False

        )   

        is_default = (
            True if request.POST.get("is_default")
            else False
        )
        

        # =========================================
        # REQUIRED VALIDATION
        # =========================================

        if not color:

            messages.error(
                request,
                "Color is required"
            )

            return redirect(
                "admin_products:edit_variant",
                variant_id=variant.id
            )

        if not size:

            messages.error(
                request,
                "Size is required"
            )

            return redirect(
                "admin_products:edit_variant",
                variant_id=variant.id
            )

        if not sku:

            messages.error(
                request,
                "SKU is required"
            )

            return redirect(
                "admin_products:edit_variant",
                variant_id=variant.id
            )

        # =========================================
        # SKU VALIDATION
        # =========================================

        if Variant.objects.filter(
            sku=sku,
            is_deleted=False
            
        ).exclude(
            id=variant.id
        ).exists():

            messages.error(
                request,
                "SKU already exists"
            )

            return redirect(
                "admin_products:edit_variant",
                variant_id=variant.id
            )

        # =========================================
        # DUPLICATE VARIANT VALIDATION
        # =========================================

        if Variant.objects.filter(

            product=product,

            color=color,

            size=size,

            is_deleted=False

        ).exclude(
            id=variant.id
        ).exists():

            messages.error(
                request,
                "This variant already exists"
            )

            return redirect(
                "admin_products:edit_variant",
                variant_id=variant.id
            )

        # =========================================
        # STOCK VALIDATION
        # =========================================

        try:

            stock = int(stock)

            if stock < 0:

                messages.error(
                    request,
                    "Stock cannot be negative"
                )

                return redirect(
                    "admin_products:edit_variant",
                    variant_id=variant.id
                )

        except ValueError:

            messages.error(
                request,
                "Invalid stock value"
            )

            return redirect(
                "admin_products:edit_variant",
                variant_id=variant.id
            )

        # =========================================
        # PRICE VALIDATION
        # =========================================

        try:

            price = float(price)

            if price < 0:

                messages.error(
                    request,
                    "Price cannot be negative"
                )

                return redirect(
                    "admin_products:edit_variant",
                    variant_id=variant.id
                )

        except ValueError:

            messages.error(
                request,
                "Invalid price value"
            )

            return redirect(
                "admin_products:edit_variant",
                variant_id=variant.id
            )

        # =========================================
        # UPDATE VARIANT
        # =========================================

        variant.color = color

        variant.size = size

        variant.sku = sku

        variant.stock = stock

        variant.price = price

        variant.is_active = is_active

        variant.is_default = is_default

        # =========================================
        # SINGLE DEFAULT VARIANT
        # =========================================

        if is_default:

            Variant.objects.filter(
                product=product
            ).exclude(
                id=variant.id
            ).update(
                is_default=False
            )

        variant.save()

        

        # =========================================
        # IMAGE VALIDATION
        # =========================================

        images = request.FILES.getlist("images")

        valid_images = [
            image for image in images
            if image and image.name
        ]

        existing_image_count = variant.images.count()

        # IF USER UPLOADS NEW IMAGES,
        # OLD IMAGES WILL BE REPLACED

        if valid_images:

            total_images = len(valid_images)

        else:

            total_images = existing_image_count

        # MINIMUM 3 IMAGES REQUIRED

        if total_images < 3:

            messages.error(
                request,
                "Minimum 3 images are required"
            )

            return redirect(
                "admin_products:edit_variant",
                variant_id=variant.id
            )

        # MAXIMUM 4 IMAGES

        if total_images > 4:

            messages.error(
                request,
                "Maximum 4 images allowed"
            )

            return redirect(
                "admin_products:edit_variant",
                variant_id=variant.id
            )

        # =========================================
        # UPDATE IMAGES
        # =========================================

        if valid_images:

            variant.images.all().delete()

            for index, image in enumerate(valid_images):

                ProductImage.objects.create(

                    variant=variant,

                    image=image,

                    is_primary=True if index == 0 else False

                )
        # =========================================
        # SUCCESS
        # =========================================

        messages.success(
            request,
            "Variant updated successfully"
        )

        return redirect(
            "admin_products:variant_management",
            product_id=product.id
        )

    # =========================================
    # GET PAGE
    # =========================================

    existing_images = variant.images.count()

    remaining_slots = range(4 - existing_images)

    return render(

        request,

        "edit_variant.html",

        {

            "variant": variant,

            "product": product,

            "remaining_slots": remaining_slots,

        }

    )

@never_cache
@login_required(login_url='login')
def delete_variant(request, variant_id):

    variant = Variant.objects.filter(
        id=variant_id
    ).first()

    # already deleted or missing
    if not variant:

        messages.error(
            request,
            "Variant already deleted"
        )

        return redirect(
            "admin_products:product_management"
        )

    if request.method == "POST":

        product_id = variant.product.id

        # 🔥 FULL DELETE
        variant.delete()

        messages.success(
            request,
            "Variant deleted successfully"
        )

        return redirect(
            "admin_products:variant_management",
            product_id=product_id
        )

    return render(
        request,
        "delete_variant.html",
        {
            "variant": variant,
            "product": variant.product,
        }
    )