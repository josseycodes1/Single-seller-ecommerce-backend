import requests
import json
from django.conf import settings
from django.core.exceptions import ValidationError

class PaystackService:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.base_url = "https://api.paystack.co"
    
    def _make_request(self, method, endpoint, data=None):
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, headers=headers)
            elif method == "GET":
                response = requests.get(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Paystack API Error: {e}")
            raise ValidationError(f"Payment service error: {str(e)}")
    
    def initialize_payment(self, email, amount, reference, callback_url=None):
        """Initialize payment with Paystack"""
        amount_in_kobo = int(amount * 100)  # Paystack uses kobo
        
        data = {
            "email": email,
            "amount": amount_in_kobo,
            "reference": reference,
            "callback_url": callback_url,
            "currency": "NGN"
        }
        
        response = self._make_request("POST", "/transaction/initialize", data)
        return response
    
    def verify_payment(self, reference):
        """Verify payment status with Paystack"""
        response = self._make_request("GET", f"/transaction/verify/{reference}")
        return response
    
    def create_transfer_recipient(self, name, account_number, bank_code):
        """Create transfer recipient for sellers (optional)"""
        data = {
            "type": "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN"
        }
        
        response = self._make_request("POST", "/transferrecipient", data)
        return response