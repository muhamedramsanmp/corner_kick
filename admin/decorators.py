from functools import wraps

from django.shortcuts import redirect


def admin_required(view_func):

    @wraps(view_func)

    def wrapper(request, *args, **kwargs):

        # NOT LOGGED IN

        if not request.user.is_authenticated:

            return redirect(
                'admin_login'
            )

        # BLOCK NORMAL USERS

        if not request.user.is_staff:

            return redirect(
                'home'
            )

        # ALLOW ADMIN

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper