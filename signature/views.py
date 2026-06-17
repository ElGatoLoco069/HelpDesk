from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect
from django.views.generic import View


# Create your views here.
@method_decorator(login_required(login_url="/"), name="dispatch")
class SignatureView(View):
    
    def get(self, request):
        
        return render(request, 
                      "new_signature.html",
                      {
                          "active_page":"new_signature",
                      })