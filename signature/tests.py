from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class SignatureViewTests(TestCase):

    def test_signature_page_loads_export_dependencies_in_order(self):
        user = User.objects.create_user(username="signature-user")
        self.client.force_login(user)

        response = self.client.get(reverse("new_signature"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="signature"')
        self.assertContains(response, 'id="downloadBtn"')
        self.assertContains(response, 'id="telefone"')
        self.assertContains(response, 'id="previewTelefone"')
        self.assertContains(response, "html2canvas.min.js")
        self.assertContains(response, "js/signature.js")

        html = response.content.decode()
        self.assertLess(html.index("html2canvas.min.js"), html.index("js/signature.js"))
