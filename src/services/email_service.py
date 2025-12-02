import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from src.utils.logger import log

class EmailService:
    def __init__(self, sender_email, sender_password, smtp_server="smtp.gmail.com", port=587):
        self.sender_email = sender_email
        self.password = sender_password
        self.smtp_server = smtp_server
        self.port = port

    def send_report(self, recipients_list, execution_results):
        """
        recipients_list: Lista de emails ['a@a.com', 'b@b.com']
        execution_results: Lista de diccionarios [{'agencia': 'Poker', 'status': 'success', 'msg': 'Enviado OK'}]
        """
        if not recipients_list:
            log.warning("No hay destinatarios de correo configurados. Saltando reporte.")
            return

        subject = f"📊 Reporte Bot Telegram - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        # Construir el cuerpo del mensaje (HTML simple para que se vea bonito)
        body_html = self._generate_html_body(execution_results)

        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = ", ".join(recipients_list)
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))

        try:
            server = smtplib.SMTP(self.smtp_server, self.port)
            server.starttls() # Encriptación
            server.login(self.sender_email, self.password)
            server.sendmail(self.sender_email, recipients_list, msg.as_string())
            server.quit()
            log.info(f"Reporte por correo enviado a {len(recipients_list)} destinatarios.")
        except Exception as e:
            log.error(f"Fallo al enviar el correo de reporte: {e}")

    def _generate_html_body(self, results):
        """Crea una tabla HTML con los resultados"""
        rows = ""
        for item in results:
            # Definir color según estado
            color = "black"
            icon = "⚪"
            if item['status'] == 'success':
                color = "green"
                icon = "✅"
            elif item['status'] == 'error':
                color = "red"
                icon = "❌"
            elif item['status'] == 'skipped':
                color = "gray"
                icon = "⏭️"

            rows += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{icon} <b>{item['agencia']}</b></td>
                <td style="padding:8px; border-bottom:1px solid #ddd; color:{color};">{item['msg']}</td>
            </tr>
            """

        return f"""
        <html>
            <body>
                <h2>Resumen de Ejecución Automática</h2>
                <p>El bot ha finalizado su ciclo de revisión. Aquí están los resultados:</p>
                <table style="width:100%; border-collapse: collapse; text-align: left;">
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding:10px;">Agencia / Carpeta</th>
                        <th style="padding:10px;">Estado</th>
                    </tr>
                    {rows}
                </table>
                <p style="font-size:12px; color:gray;">Este es un mensaje automático. No responder.</p>
            </body>
        </html>
        """