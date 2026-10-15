from rest_framework.test import APIClient

PASSWORD = "Clave-segura-1"


def refresh_csrf(client: APIClient) -> None:
    client.get("/api/v1/auth/csrf/")
    token = client.cookies["csrftoken"].value
    client.credentials(HTTP_X_CSRFTOKEN=token)


def register(client, email="ana@ejemplo.test", password=PASSWORD, **extra):
    response = client.post(
        "/api/v1/auth/register/",
        {"email": email, "password": password, **extra},
        format="json",
    )
    refresh_csrf(client)
    return response
