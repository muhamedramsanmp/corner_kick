from functools import wraps

from django.shortcuts import redirect


def user_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:

            return redirect("login")

        if request.user.is_staff:

            return redirect("admin_dashboard")

        return view_func(request, *args, **kwargs)

    return wrapper
