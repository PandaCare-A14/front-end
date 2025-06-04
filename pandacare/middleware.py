from json import JSONDecodeError
from django.http import HttpRequest
from django.shortcuts import redirect
import jwt as pyjwt
import requests
from pandacare.settings import JWKS_URL, AUTH_API_URL


class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, req: HttpRequest):
        if req.path == "/login/":
            return self.get_response(req)

        access_token = req.session["access_token"]
        refresh_token = req.session["refresh_token"]

        if not access_token:
            return redirect("main:login", permanent=False)

        jwks_client = pyjwt.PyJWKClient(JWKS_URL, cache_keys=True)

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(access_token)
        except pyjwt.exceptions.PyJWKClientError:
            del req.session["access_token"]
            del req.session["refresh_token"]

            return redirect("main:login", permanent=True)

        try:
            claims: dict = pyjwt.decode(
                access_token,
                signing_key,
                algorithms=["RS256"],
                options={"require": ["exp"], "verify_exp": True},
            )

            req.session["user_id"] = claims["user_id"]

            return self.get_response(req)
        except pyjwt.ExpiredSignatureError:
            print("I got here")
            try:
                access, refresh = refresh_expired_token(refresh_token)
                req.session["access_token"] = access
                req.session["refresh_token"] = refresh

                print("I got here 2")
                return self.get_response(req)

            except JSONDecodeError:
                print("Response returned by server was invalid JSON")
            except requests.RequestException as err:
                print(err)
                return redirect("main:login", permanent=False)


def refresh_expired_token(refresh_token: str) -> tuple[str, str]:
    res: requests.Response = requests.post(
        f"{AUTH_API_URL}/api/token/refresh", json={"refresh_token": refresh_token}
    )
    print(res.ok)
    if res.ok:
        tokens = res.json()

        access = tokens["access"]
        refresh = tokens["refresh"]

        return (access, refresh)
    else:
        raise requests.RequestException(
            {"message": "Something wrong happened while trying to fetch refresh token"}
        )
