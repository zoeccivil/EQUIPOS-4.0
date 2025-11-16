import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class SMTPUtils:
    """Utilidad para operaciones básicas con servidores SMTP."""

    @staticmethod
    def enviar_email(servidor, puerto, usuario, password, destinatario, asunto, mensaje, html=False):
        """Envía un correo utilizando SMTP."""
        msg = MIMEMultipart()
        msg['From'] = usuario
        msg['To'] = destinatario
        msg['Subject'] = asunto

        cuerpo = MIMEText(mensaje, 'html' if html else 'plain')
        msg.attach(cuerpo)

        try:
            with smtplib.SMTP(servidor, puerto) as server:
                server.starttls()
                server.login(usuario, password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error enviando correo SMTP: {e}")
            return False
