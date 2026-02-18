import io
from urllib.parse import urlsplit


def _build_environ_from_vercel_request(request):
    """Build a WSGI environ dict from a Vercel request-like object.

    This is a lightweight implementation intended to work with the
    request object provided by Vercel's Python runtime. It also includes
    reasonable fallbacks so the same adapter can be used in local tests.
    """
    headers = {}
    try:
        headers = dict(request.headers)
    except Exception:
        # request.headers might already be a dict-like object
        try:
            headers = {k: v for k, v in request.headers.items()}
        except Exception:
            headers = {}

    url = getattr(request, "url", None) or getattr(request, "path", "/")
    parsed = urlsplit(url)

    body = None
    # request.body is the most likely name; try a few fallbacks
    if hasattr(request, "body"):
        body = request.body
    else:
        get_data = getattr(request, "get_data", None)
        if callable(get_data):
            body = get_data()

    if body is None:
        body = b""
    if isinstance(body, str):
        body = body.encode("utf-8")

    host_header = headers.get("host", "localhost")
    if ":" in host_header:
        server_name, server_port = host_header.split(":", 1)
    else:
        server_name = host_header
        server_port = "80"

    environ = {
        "REQUEST_METHOD": getattr(request, "method", "GET"),
        "SCRIPT_NAME": "",
        "PATH_INFO": parsed.path or "/",
        "QUERY_STRING": parsed.query or "",
        "CONTENT_TYPE": headers.get("content-type", ""),
        "CONTENT_LENGTH": str(len(body)) if body is not None else "0",
        "SERVER_NAME": server_name,
        "SERVER_PORT": server_port,
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": parsed.scheme or "http",
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": io.StringIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }

    # Map headers to HTTP_* environ
    for key, value in headers.items():
        header_name = "HTTP_" + key.upper().replace("-", "_")
        # CONTENT_TYPE and CONTENT_LENGTH are special-cased
        if header_name in ("HTTP_CONTENT_TYPE", "HTTP_CONTENT_LENGTH"):
            continue
        environ[header_name] = value

    return environ


def handle_request(app, request, response=None):
    """Adapt a Flask WSGI app to a Vercel Python function.

    - `app` should be a Flask application instance
    - `request` is the incoming Vercel request-like object
    - `response` is the Vercel response object (optional)

    If `response` is provided we set its status/headers/body via the
    expected `set_header` / `send` API; otherwise we return a tuple
    (body_bytes, status_code, headers) as a fallback.
    """
    environ = _build_environ_from_vercel_request(request)

    status_headers = {}

    def start_response(status, headers, exc_info=None):
        status_headers["status"] = status
        status_headers["headers"] = headers

    result = app.wsgi_app(environ, start_response)
    try:
        body = b"".join(result)
    finally:
        if hasattr(result, "close"):
            try:
                result.close()
            except Exception:
                pass

    status = status_headers.get("status", "200 OK")
    headers = status_headers.get("headers", [])

    # If a Vercel response object is present, use its API
    if response is not None:
        # status like '200 OK'
        try:
            response.status_code = int(status.split()[0])
        except Exception:
            response.status_code = 200
        for name, value in headers:
            # response.set_header is used by vercel-wsgi; tolerate absence
            try:
                response.set_header(name, value)
            except Exception:
                try:
                    # some runtimes expose headers as dict
                    response.headers[name] = value
                except Exception:
                    pass
        # send the body
        try:
            response.send(body)
            return response
        except Exception:
            # fallback: return raw tuple
            return (body, response.status_code, dict(headers))

    # No response object available — return tuple (body, status_code, headers)
    try:
        status_code = int(status.split()[0])
    except Exception:
        status_code = 200

    return (body, status_code, dict(headers))
