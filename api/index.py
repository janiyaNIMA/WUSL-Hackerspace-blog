from app import app
from vercel_wsgi import handle_request


def handler(request, response=None):
    return handle_request(app, request, response)
