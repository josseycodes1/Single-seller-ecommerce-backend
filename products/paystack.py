import requests
import json
import logging
from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class PaystackService:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.base_url = "https://api.paystack.co"
        
        # Validate that keys are set
        if not self.secret_key:
            logger.error("PAYSTACK_SECRET_KEY is not configured in settings")
            raise ValidationError("Paystack secret key is not configured")
    
    def _make_request(self, method, endpoint, data=None, timeout=30):
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        logger.info(f"Paystack API Request: {method} {endpoint}")
        if data:
            logger.debug(f"Request data: {self._sanitize_data(data)}")
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            else:
                error_msg = f"Unsupported HTTP method: {method}"
                logger.error(error_msg)
                raise ValidationError(error_msg)
            
            # Log response status
            logger.info(f"Paystack API Response Status: {response.status_code}")
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                logger.debug(f"Paystack API Response: {response_data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Paystack JSON response: {e}")
                raise ValidationError(f"Invalid response from payment service: {response.text}")
            
            # Check for HTTP errors
            response.raise_for_status()
            
            return response_data
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Paystack API timeout after {timeout}s: {str(e)}"
            logger.error(error_msg)
            raise ValidationError(f"Payment service timeout: Please try again")
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Paystack API connection error: {str(e)}"
            logger.error(error_msg)
            raise ValidationError(f"Unable to connect to payment service")
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Paystack API HTTP error {response.status_code}: {str(e)}"
            logger.error(error_msg)
            
            # Provide more specific error messages based on status code
            if response.status_code == 401:
                raise ValidationError("Payment service authentication failed")
            elif response.status_code == 400:
                # Try to get error details from response
                try:
                    error_detail = response.json().get('message', 'Invalid request')
                    raise ValidationError(f"Payment request failed: {error_detail}")
                except:
                    raise ValidationError("Invalid payment request")
            elif response.status_code == 403:
                raise ValidationError("Payment service access denied")
            elif response.status_code >= 500:
                raise ValidationError("Payment service is temporarily unavailable")
            else:
                raise ValidationError(f"Payment service error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Paystack API request exception: {str(e)}"
            logger.error(error_msg)
            raise ValidationError(f"Payment service error: {str(e)}")
            
        except Exception as e:
            error_msg = f"Unexpected error in Paystack API call: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValidationError(f"Unexpected payment service error")
    
    def _sanitize_data(self, data):
        """Sanitize sensitive data for logging"""
        sanitized = data.copy()
        
        # Remove or mask sensitive fields
        sensitive_fields = ['authorization_code', 'bin', 'last4', 'authorization_url']
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = '***'
                
        return sanitized
    
    def initialize_payment(self, email, amount, reference, callback_url=None, metadata=None):
            """Initialize payment with Paystack"""
            logger.info(f"Initializing payment - Email: {email}, Amount: {amount}, Reference: {reference}")
            
            # Validate inputs
            if not email or not isinstance(email, str) or "@" not in email:
                raise ValidationError("Valid email is required for payment")
            
            if not amount or amount <= 0:
                raise ValidationError("Payment amount must be greater than 0")
            
            if not reference or not isinstance(reference, str):
                raise ValidationError("Valid payment reference is required")
            
            try:
                amount_in_kobo = int(amount * 100)  # Convert to kobo
                if amount_in_kobo < 100:  # Paystack minimum amount
                    raise ValidationError("Payment amount is too small")
                    
            except (ValueError, TypeError) as e:
                raise ValidationError(f"Invalid amount format: {amount}")
            
            data = {
                "email": email,
                "amount": amount_in_kobo,
                "reference": reference,
                "currency": "NGN"
            }
            
            # Add callback URL if provided
            if callback_url:
                data["callback_url"] = callback_url
                logger.info(f"Using callback URL: {callback_url}")
            
            # ✅ ADD METADATA IF PROVIDED
            if metadata:
                data["metadata"] = metadata
                logger.info(f"Added metadata to payment: {self._sanitize_data(metadata)}")
            
            try:
                response = self._make_request("POST", "/transaction/initialize", data)
                
                # Validate response structure
                if not response.get('status'):
                    error_msg = response.get('message', 'Unknown Paystack error')
                    logger.error(f"Paystack initialization failed: {error_msg}")
                    raise ValidationError(f"Payment initialization failed: {error_msg}")
                
                if not response.get('data') or not response['data'].get('authorization_url'):
                    logger.error(f"Invalid Paystack response structure: {response}")
                    raise ValidationError("Invalid response from payment service")
                
                logger.info(f"Payment initialized successfully - Reference: {reference}")
                return response
                
            except ValidationError:
                # Re-raise ValidationErrors
                raise
            except Exception as e:
                logger.error(f"Unexpected error in payment initialization: {str(e)}", exc_info=True)
                raise ValidationError("Failed to initialize payment")
    
    def verify_payment(self, reference):
        """Verify payment status with Paystack"""
        logger.info(f"Verifying payment - Reference: {reference}")
        
        if not reference:
            raise ValidationError("Payment reference is required for verification")
        
        try:
            response = self._make_request("GET", f"/transaction/verify/{reference}")
            
            # Validate response structure
            if not response.get('status'):
                error_msg = response.get('message', 'Unknown verification error')
                logger.error(f"Paystack verification failed: {error_msg}")
                raise ValidationError(f"Payment verification failed: {error_msg}")
            
            logger.info(f"Payment verification completed - Reference: {reference}, Status: {response.get('data', {}).get('status')}")
            return response
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in payment verification: {str(e)}", exc_info=True)
            raise ValidationError("Failed to verify payment")
    
    def create_transfer_recipient(self, name, account_number, bank_code):
        """Create transfer recipient for sellers (optional)"""
        logger.info(f"Creating transfer recipient - Name: {name}, Bank: {bank_code}")
        
        # Validate inputs
        if not all([name, account_number, bank_code]):
            raise ValidationError("Name, account number, and bank code are required")
        
        data = {
            "type": "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN"
        }
        
        try:
            response = self._make_request("POST", "/transferrecipient", data)
            
            if not response.get('status'):
                error_msg = response.get('message', 'Unknown recipient creation error')
                logger.error(f"Transfer recipient creation failed: {error_msg}")
                raise ValidationError(f"Recipient creation failed: {error_msg}")
            
            logger.info(f"Transfer recipient created successfully - Name: {name}")
            return response
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in recipient creation: {str(e)}", exc_info=True)
            raise ValidationError("Failed to create transfer recipient")

    def check_balance(self):
        """Check Paystack account balance (optional)"""
        try:
            response = self._make_request("GET", "/balance")
            return response
        except Exception as e:
            logger.error(f"Balance check failed: {str(e)}")
            raise ValidationError("Failed to check account balance")