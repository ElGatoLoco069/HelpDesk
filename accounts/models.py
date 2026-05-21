from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    telefone = models.CharField(max_length=20)
    departamento = models.CharField(max_length=100)
    foto = models.ImageField(upload_to='usuarios/', null=True, blank=True)

    is_support = models.BooleanField(default=False)
    ticket_auto_refresh_seconds = models.PositiveSmallIntegerField(default=30)

    def __str__(self):
        return self.user.username
