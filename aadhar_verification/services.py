import requests
import json
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings
from .models import APIToken, APIConfig, VerificationLog
import logging

logger = logging.getLogger(__name__)

class AadharVerificationService:
    def __init__(self):
        self.config = APIConfig.objects.filter(is_active=True).first()
        if not self.config:
            raise Exception("No active API configuration found")
        
        self.base_url = self.config.base_url
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'x-api-key': self.config.api_key,
            'x-api-version': self.config.api_version
        }

    def _get_access_token(self):
        """Get or refresh access token"""
        # Check for valid token
        valid_token = APIToken.objects.filter(
            config=self.config,
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
        
        if valid_token:
            return valid_token.access_token
        
        # Generate new token
        return self._generate_new_token()

    def _generate_new_token(self):
        """Generate new access token"""
        url = f"{self.base_url}/authenticate"
        
        headers = {
            'Accept': 'application/json',
            'x-api-key': self.config.api_key,
            'x-api-secret': self.config.api_secret
        }

        try:
            response = requests.post(url, headers=headers, data="")
            response_data = response.json()
            
            # Log the request
            VerificationLog.objects.create(
                log_type='token_generation',
                request_data={},
                response_data=response_data,
                status_code=response.status_code
            )

            if response.status_code == 200:
                access_token = response_data.get('access_token')
                data = response_data.get('data', {})
                
                # Calculate expiration time (usually 24 hours from response timestamp)
                timestamp = response_data.get('timestamp')
                if timestamp:
                    expires_at = datetime.fromtimestamp(timestamp/1000) + timedelta(hours=24)
                else:
                    expires_at = timezone.now() + timedelta(hours=24)
                
                # Deactivate old tokens
                APIToken.objects.filter(config=self.config, is_active=True).update(is_active=False)
                
                # Create new token
                token = APIToken.objects.create(
                    config=self.config,
                    access_token=access_token,
                    expires_at=expires_at,
                    is_active=True
                )
                
                return access_token
            else:
                logger.error(f"Token generation failed: {response_data}")
                raise Exception(f"Token generation failed: {response_data.get('message', 'Unknown error')}")
                
        except requests.RequestException as e:
            logger.error(f"Token generation request failed: {str(e)}")
            VerificationLog.objects.create(
                log_type='error',
                error_message=f"Token generation request failed: {str(e)}",
                status_code=500
            )
            raise

    def _make_api_call(self, url, payload, method='POST'):
        """Make API call with error handling and logging"""
        access_token = self._get_access_token()
        
        headers = self.headers.copy()
        headers['Authorization'] = access_token
        
        try:
            if method.upper() == 'POST':
                response = requests.post(url, headers=headers, data=json.dumps(payload))
            else:
                response = requests.get(url, headers=headers)
            
            response_data = response.json()
            
            # Log the API call
            log_type = 'otp_request' if 'otp' in url and 'verify' not in url else 'otp_verification'
            VerificationLog.objects.create(
                log_type=log_type,
                request_data=payload,
                response_data=response_data,
                status_code=response.status_code
            )

            return response_data
            
        except requests.RequestException as e:
            logger.error(f"API call failed: {str(e)}")
            VerificationLog.objects.create(
                log_type='error',
                error_message=f"API call failed: {str(e)}",
                status_code=500
            )
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            VerificationLog.objects.create(
                log_type='error',
                error_message=f"JSON decode error: {str(e)}",
                status_code=500
            )
            raise

    def generate_otp(self, aadhaar_number, consent="Y", reason="Aadhaar Verification"):
        """Generate OTP for Aadhaar verification"""
        url = f"{self.base_url}/kyc/aadhaar/okyc/otp"
        
        payload = {
            "@entity": "in.co.sandbox.kyc.aadhaar.okyc.otp.request",
            "aadhaar_number": aadhaar_number,
            "consent": consent,
            "reason": reason
        }
        
        try:
            response = self._make_api_call(url, payload)
            
            if response.get('code') == 200:
                data = response.get('data', {})
                return {
                    'success': True,
                    'reference_id': data.get('reference_id'),
                    'message': data.get('message'),
                    'transaction_id': response.get('transaction_id')
                }
            else:
                return {
                    'success': False,
                    'message': response.get('message', 'OTP generation failed'),
                    'error_code': response.get('code'),
                    'transaction_id': response.get('transaction_id')
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"Service error: {str(e)}"
            }

    def verify_otp(self, reference_id, otp):
        """Verify OTP and get Aadhaar details"""
        url = f"{self.base_url}/kyc/aadhaar/okyc/otp/verify"
        
        payload = {
            "@entity": "in.co.sandbox.kyc.aadhaar.okyc.request",
            "reference_id": reference_id,
            "otp": otp
        }
        
        try:
            response = self._make_api_call(url, payload)
            
            if response.get('code') == 200:
                data = response.get('data', {})
                return {
                    'success': True,
                    'data': data,
                    'transaction_id': response.get('transaction_id')
                }
            else:
                return {
                    'success': False,
                    'message': response.get('message', 'OTP verification failed'),
                    'error_code': response.get('code'),
                    'transaction_id': response.get('transaction_id')
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"Service error: {str(e)}"
            }