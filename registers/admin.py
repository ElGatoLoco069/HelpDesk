from django.contrib import admin
from registers.models import Priority, AssignmentMethod, Category, Subcategory

# Register your models here.

@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        "first_interaction_limit",
        "estimated_service_time",
        'created_at', 'updated_at')
    search_fields = ('name',)


@admin.register(AssignmentMethod)
class AssingmentMethodAdmin(admin.ModelAdmin): 
    list_display = ('method_type', 'created_at', 'updated_at')
    search_fields = ('method_type',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    
@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "name",
        "priority",
        "assignment_method",
        )
    
    search_fields = ('name',)
    