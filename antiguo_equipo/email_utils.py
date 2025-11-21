import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailUtils:
    """Utilidad para envío básico de correos electrónicos."""

    def __init__(self, servidor, puerto, usuario, password):
        self.servidor = servidor
        self.puerto = puerto
        self.usuario = usuario
        self.password = password

    def enviar_email(self, destinatario, asunto, mensaje, html=False):
        msg = MIMEMultipart()
        msg['From'] = self.usuario
        msg['To'] = destinatario
        msg['Subject'] = asunto

        if html:
            msg.attach(MIMEText(mensaje, 'html'))
        else:
            msg.attach(MIMEText(mensaje, 'plain'))

        try:
            with smtplib.SMTP(self.servidor, self.puerto) as server:
                server.starttls()
                server.login(self.usuario, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error enviando correo: {e}")
            return False
