"""SAFE-PATH - Túnel público y QR para acceso móvil."""

import subprocess
import sys


def start_tunnel(port: int) -> str:
    """Abre túnel ngrok al puerto dado (o usa IP local si falla).

    Imprime QR en terminal y copia la URL /mobile al portapapeles.
    Devuelve la URL base (sin /mobile).
    """
    base_url = _open_tunnel(port)
    mobile_url = base_url + "/mobile"
    _print_qr(mobile_url)
    _copy_to_clipboard(mobile_url)
    print(f"  Vista móvil : {mobile_url}")
    print("  (URL copiada al portapapeles)")
    return base_url


def _open_tunnel(port: int) -> str:
    try:
        from pyngrok import ngrok

        tunnel = ngrok.connect(port, "http")
        return tunnel.public_url
    except Exception:
        from safepath_mvp.shared.utils import get_local_ip

        return f"http://{get_local_ip()}:{port}"


def _print_qr(url: str) -> None:
    try:
        import io
        import sys

        import qrcode

        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)

        buf = io.StringIO()
        qr.print_ascii(out=buf, invert=True)
        qr_str = "\n" + buf.getvalue() + "\n"

        # En Windows la consola puede ser cp1252; forzamos UTF-8.
        try:
            sys.stdout.buffer.write(qr_str.encode("utf-8"))
            sys.stdout.buffer.flush()
        except AttributeError:
            sys.stdout.write(qr_str)
    except Exception:
        pass


def _copy_to_clipboard(url: str) -> None:
    try:
        if sys.platform == "win32":
            subprocess.run(["clip"], input=url.encode(), check=True)
        elif sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=url.encode(), check=True)
        else:
            subprocess.run(["xclip", "-selection", "clipboard"], input=url.encode(), check=True)
    except Exception:
        pass
