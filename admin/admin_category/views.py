from django.shortcuts import render,redirect,get_object_or_404
from .models import Category
from django.contrib import messages
from .models import Category
from django.core.paginator import Paginator
from django.db.models import Q,Count
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache



@never_cache
@login_required(login_url='login')
def category_management(request):

    query = request.GET.get("q", "")

    categories_list = Category.objects.filter(
        is_deleted=False
    ).annotate(
        product_count  = Count('products')
    )


    if query:

        categories_list = categories_list.filter(

            Q(category_name__icontains=query) |

            Q(description__icontains=query)

        )

    categories_list = categories_list.order_by(
        '-created_at'
    )


    paginator = Paginator(
        categories_list,
        5
    )

    page_number = request.GET.get('page')

    categories = paginator.get_page(page_number)

    context = {

        "categories": categories,

        "total_categories": categories_list.count(),

        "active_categories": categories_list.filter(
            is_active=True
        ).count(),

        "inactive_categories": categories_list.filter(
            is_active=False
        ).count(),

        "query": query,
    }

    return render(
        request,
        "category_management.html",
        context
    )

def add_category(request):

    if request.method == "POST":

        category_name = request.POST.get(
            "name",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        category_img = request.FILES.get("image")

        is_active = request.POST.get("is_active")

        if not category_name:

            messages.error(
                request,
                "Category name is required"
            )

            return redirect("add_category")

        if Category.objects.filter(
            category_name__iexact=category_name,
            is_deleted=False
        ).exists():

            messages.error(
                request,
                "Category already exists"
            )

            return redirect("add_category")
        

        # CREATE CATEGORY

        Category.objects.create(

            category_name=category_name,

            category_img=category_img,

            description=description,

            is_active=True if is_active else False
        )

        messages.success(
            request,
            "Category added successfully"
        )

        return redirect("category_management")

    return render(
        request,
        "add_category.html"
    )


def edit_category(request, category_id):

    category = get_object_or_404(
        Category,
        id=category_id
    )

    if request.method == "POST":

        category_name = request.POST.get(
            "name",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        category_img = request.FILES.get(
            "category_img"
        )

        # STATUS

        is_active = (
            True if request.POST.get("is_active")
            else False
        )

        # EMPTY VALIDATION

        if not category_name:

            messages.error(
                request,
                "Category name is required"
            )

            return redirect(
                "edit_category",
                category_id=category.id
            )

        # DUPLICATE CHECK

        if Category.objects.filter(
            category_name__iexact=category_name
        ).exclude(id=category.id).exists():

            messages.error(
                request,
                "Category already exists"
            )

            return redirect(
                "edit_category",
                category_id=category.id
            )

        # UPDATE

        category.category_name = category_name

        category.description = description

        category.is_active = (
            True if request.POST.get("is_active")
            else False
        )


        if category_img:

            category.category_img = category_img

        category.save()

        messages.success(
            request,
            "Category updated successfully"
        )

        return redirect(
            "category_management"
        )

    return render(

        request,

        "edit_category.html",

        {
            "category": category
        }

    )

def toggle_category_status(request, category_id):

    category = get_object_or_404(
        Category,
        id=category_id
    )

    # TOGGLE STATUS

    category.is_active = not category.is_active

    category.save()

    # SUCCESS MESSAGE

    if category.is_active:

        messages.success(
            request,
            f"{category.category_name} activated successfully"
        )

    else:

        messages.success(
            request,
            f"{category.category_name} deactivated successfully"
        )

    return redirect("category_management")



@never_cache
@login_required(login_url='login')
def delete_category(request, category_id):

    category = Category.objects.filter(
        id=category_id
    ).first()
    
    if not category or category.is_deleted:

        messages.error(
            request,
            "Category already deleted"
        )

        return redirect(
            "category_management"
        )

    if request.method == "POST":


        category.delete()

        messages.success(
            request,
            "Category deleted successfully"
        )

        return redirect(
            "category_management"
        )

    return render(
        request,
        "delete_category.html",
        {
            "category": category
        }
    )