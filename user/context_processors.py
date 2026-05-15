from user.accounts.models import Profile
from user.products.models import CartItem
from user.products.models import Wishlist

def user_profile(request):
    if request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return {"profile": profile}
    return {}




def navbar_counts(request):

    cart_count = 0

    wishlist_count = 0

    if request.user.is_authenticated:

        cart_count = CartItem.objects.filter(

            cart__user=request.user

        ).count()

        wishlist_count = Wishlist.objects.filter(

            user=request.user

        ).count()

    return {

        "cart_count": cart_count,

        "wishlist_count": wishlist_count,

    }