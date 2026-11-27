def get_client_ips(request):
    return [
        request.client.host,
        request.headers.get("X-Forwarded-For", None), 
        request.headers.get("X-Real-IP", None)
    ]

