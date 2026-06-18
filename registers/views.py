from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages

from django.http import JsonResponse
from registers.models import AssignmentMethod, Category, Priority, Subcategory


def user_is_support(user):
    try:
        return user.is_superuser or user.profile.is_support
    except Exception:
        return user.is_superuser

@method_decorator(login_required(login_url="/"), name="dispatch")
class CategoryView(View):
    
    def get(self, request):
        
        try: 
            if not user_is_support(request.user):
                messages.warning(request, "Apenas usuarios de suporte podem acessar cadastros.")
                return redirect("home")
            
            categories = Category.objects.filter(status=True)
            priorities = Priority.objects.filter(status=True)
            assignment_methods = AssignmentMethod.objects.filter(status=True)
            
            return render(
                request, 
                "new_category.html", 
                {
                    "active_page":"categories",
                    "categories":categories,
                    "priorities":priorities,
                    "assignment_methods":assignment_methods,
                    
                })
        
        except Exception as e:
            print(e)
            messages.error(request, "Erro ao carregar categorias")
            return redirect("home")
        
    
    def post(self, request):
        
        try:
            if not user_is_support(request.user):
                messages.warning(request, "Apenas usuarios de suporte podem alterar cadastros.")
                return redirect("home")
            
            action = request.POST.get("action")
            
            if action == "delete":
                self.delete(request)
                
            elif action == "create":
                self.create(request)
                
            elif action == "update":
                self.update(request)    

            elif action == "create_subcategory":
                self.create_subcategory(request)

            elif action == "update_subcategory":
                self.update_subcategory(request)

            elif action == "delete_subcategory":
                self.delete_subcategory(request)
            
                
            return redirect("categories")
        
        except Exception as e:
            print(e)
            messages.error(request, "Erro ao salvar categoria")
            return redirect("home")
        
    
    def create(self, request):
        try: 
        
            name = (request.POST.get("category_name") or "").strip()

            if not name:
                messages.warning(request, "Informe o nome da categoria.")
                return redirect("categories")
            
            if Category.objects.filter(name=name).exists():
                messages.warning(request, "Categoria ja cadastrada!")
                return redirect("categories")
                
            
            new_category = Category.objects.create()
            new_category.name = name
            new_category.save()
            
            messages.success(request, "Categoria cadastrada com Sucesso!")
        
        except Exception as e:
            print(e)
            messages.error(request, "Erro ao criar categoria")
            return redirect("categories")
            
            
    def update(self, request):
        
        try:
            id = request.POST.get("category_id")
            new_name = (request.POST.get("category_name") or "").strip()

            if not new_name:
                messages.warning(request, "Informe o nome da categoria.")
                return redirect("categories")
            
            if Category.objects.filter(name=new_name).exclude(id=id).exists():
                messages.warning(request, "Nao foi possivel atualizar a categoria! devido nome ja existente!")
                return redirect("categories")
            
            category = Category.objects.get(id=id)
            category.name = new_name
            category.save()
            messages.success(request, "Categoria atualizada com sucesso!")
            
        except Exception as e:
            print(e)
            messages.error(request, "Erro ao atualizar categoria")
            return redirect("categories")
       
       
    def delete(self, request):
        
        try:    
            id = request.POST.get("category_id")
            category = Category.objects.get(id=id)
            category.status = False
            category.save()
            messages.success(request, "Categoria desativada com sucesso!")
            return redirect("categories")
        
        except Exception as e:
            print(e)
            messages.error(request, "Erro ao deletar categoria")
            return redirect("categories")


    def create_subcategory(self, request):
        try:
            category_id = request.POST.get("subcategory_category_id")
            name = (request.POST.get("subcategory_name") or "").strip()
            priority_id = request.POST.get("subcategory_priority")
            assignment_method_id = request.POST.get("subcategory_assignment_method")

            if not name:
                messages.warning(request, "Informe o nome da subcategoria.")
                return redirect("categories")
            if Subcategory.objects.filter(name=name).exists():
                messages.warning(request, "Subcategoria ja cadastrada!")
                return redirect("categories")

            Subcategory.objects.create(
                category_id=category_id,
                name=name,
                priority_id=priority_id,
                assignment_method_id=assignment_method_id,
            )

            messages.success(request, "Subcategoria cadastrada com sucesso!")

        except Exception as e:
            print(e)
            messages.error(request, "Erro ao criar subcategoria")
            return redirect("categories")


    def update_subcategory(self, request):
        try:
            subcategory_id = request.POST.get("subcategory_id")
            category_id = request.POST.get("subcategory_category_id")
            name = (request.POST.get("subcategory_name") or "").strip()
            priority_id = request.POST.get("subcategory_priority")
            assignment_method_id = request.POST.get("subcategory_assignment_method")

            if not name:
                messages.warning(request, "Informe o nome da subcategoria.")
                return redirect("categories")

            if Subcategory.objects.filter(name=name).exclude(id=subcategory_id).exists():
                messages.warning(request, "Nao foi possivel atualizar a subcategoria! devido nome ja existente!")
                return redirect("categories")

            subcategory = Subcategory.objects.get(id=subcategory_id)
            subcategory.category_id = category_id
            subcategory.name = name
            subcategory.priority_id = priority_id
            subcategory.assignment_method_id = assignment_method_id
            subcategory.save()

            messages.success(request, "Subcategoria atualizada com sucesso!")

        except Exception as e:
            print(e)
            messages.error(request, "Erro ao atualizar subcategoria")
            return redirect("categories")


    def delete_subcategory(self, request):
        try:
            subcategory_id = request.POST.get("subcategory_id")
            subcategory = Subcategory.objects.get(id=subcategory_id)
            subcategory.status = False
            subcategory.save()
            messages.success(request, "Subcategoria desativada com sucesso!")

        except Exception as e:
            print(e)
            messages.error(request, "Erro ao deletar subcategoria")
            return redirect("categories")
        

@login_required(login_url="/")
def get_subcategories(request, category_id):
    subs = Subcategory.objects.select_related("priority", "assignment_method").filter(category_id=category_id, status=True)

    data = [
        {
            "id": s.id,
            "name": s.name,
            "category_id": s.category_id,
            "priority_id": s.priority_id,
            "priority_name": s.priority.name,
            "assignment_method_id": s.assignment_method_id,
            "assignment_method_name": s.assignment_method.name,
            "first_interaction_limit": s.priority.first_interaction_limit,
            "estimated_service_time": s.priority.estimated_service_time,
        }
        for s in subs
    ]

    return JsonResponse(data, safe=False)
          
        
