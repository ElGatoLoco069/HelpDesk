from django.shortcuts import render, redirect
from django.views.generic import View

# Create your views here.

class SignatureView(View):
    
    def get(self, request):
        
        return render(request, 
                      "new_signature.html",
                      {
                          "active_page":"new_signature",
                      })