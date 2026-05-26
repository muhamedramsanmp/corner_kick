from functools import wraps
from django.shortcuts import redirect

def user_required(view_func):

    @wraps(view_func)

    def wrapper(request, *args, **kwargs):

        # NOT LOGGED IN

        if not request.user.is_authenticated:

            return redirect(
                'login'
            )

        # ADMIN BLOCK

        if request.user.is_staff:

            return redirect(
                'admin_dashboard'
            )

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper