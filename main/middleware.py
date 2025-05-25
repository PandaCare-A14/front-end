from django.http import HttpRequest
from pandacare.settings import JWKS_URL
import jwt as pyjwt

def acquire_user_id(view_func):
    def wrapper(req: HttpRequest, *args, **kwargs):
        jwt = req.COOKIES.get("access")
        if not jwt:
            return {"error": "Authentication required"}

        try:
            jwks_client = pyjwt.PyJWKClient(JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(jwt)
            decoded_jwt = pyjwt.decode(jwt, signing_key.key, algorithms=["RS256"])
            req.user_id = decoded_jwt.get("user_id")  # Attach user_id to the request
        except Exception as e:
            return {"error": f"Authentication failed: {str(e)}"}

        return view_func(req, *args, **kwargs)
    return wrapper

