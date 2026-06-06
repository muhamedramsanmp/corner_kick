import random
import string

from .models import ReferralCode


def generate_referral_code():

    while True:

        code = ''.join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=8
            )
        )

        if not ReferralCode.objects.filter(
            code=code
        ).exists():

            return code