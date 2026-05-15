from django.db import models


class Category(models.Model):

    category_name = models.CharField(
        max_length=150,
    )

    category_img = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    is_deleted = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = ['-created_at']

        verbose_name = "Category"

        verbose_name_plural = "Categories"

    def __str__(self):
        return self.category_name
    

    