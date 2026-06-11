from django.db import models
from django.contrib.auth.models import User


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=50, default="")
    address_type = models.CharField(max_length=20, default="home")
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):

        if self.is_default:

            Address.objects.filter(user=self.user, is_default=True).exclude(
                id=self.id
            ).update(is_default=False)

        super().save(*args, **kwargs)
