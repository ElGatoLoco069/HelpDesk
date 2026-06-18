from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefone = models.CharField(max_length=20)
    cargo = models.CharField(max_length=100,  null=True, blank=True)
    departamento = models.CharField(max_length=100)
    foto = models.ImageField(upload_to='usuarios/', null=True, blank=True)

    is_support = models.BooleanField(default=False)
    ticket_auto_refresh_seconds = models.PositiveSmallIntegerField(default=30)

    last_activity = models.DateTimeField(null=True, blank=True)
    authenticator_secret = models.CharField(max_length=64, blank=True)
    authenticator_enabled = models.BooleanField(default=False)
    authenticator_confirmed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.user.username


class UserPreferences(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    indicators = models.BooleanField(default=True)
    service_queue = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Preferências de {self.user.username}"
    
