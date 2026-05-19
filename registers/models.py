from django.db import models

# Create your models here.

class Priority(models.Model):
    
    name = models.CharField(max_length=150, unique=True)
    first_interaction_limit = models.IntegerField()
    estimated_service_time = models.IntegerField()
    color = models.CharField(max_length=150, default="progress")
    status = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    

class AssignmentMethod(models.Model):
    
    name = models.CharField(max_length=150, unique=True)
    descript = models.TextField()
    
    status = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
        
    def __str__(self):
        return self.name


class Category(models.Model):
    
    name = models.CharField(max_length=150, unique=True)
    status = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    

class Subcategory(models.Model):
    
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    name = models.CharField(max_length=150, unique=True)
    priority = models.ForeignKey(Priority, on_delete=models.PROTECT)
    assignment_method = models.ForeignKey(AssignmentMethod, on_delete=models.PROTECT)
    
    status = models.BooleanField(default=True)
        
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name