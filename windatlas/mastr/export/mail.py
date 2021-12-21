import smtplib,ssl
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders

name_reciever = "Sebastian"

message = f"""Subject: Table from MaStR-analysis on code-de

Dear {name_reciever}, this mail contains your requested MaStR-analyse data."""

def send_mail(send_from,send_to,subject,text,path_attachment="WorkBook3.xlsx",server="smtp.gmail.com",port=465,password='',isSsl=True):
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = send_to
    msg['Date'] = formatdate(localtime = True)
    msg['Subject'] = subject
    msg.attach(MIMEText(text, "plain"))

    # Open PDF file in binary mode
    with open(path_attachment, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email    
    encoders.encode_base64(part)

    # Add header as key/value pair to attachment part
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {path_attachment}",
    )

    # Add attachment to message and convert message to string
    msg.attach(part)
    text = msg.as_string()

    # Log in to server using secure context and send email
    if isSsl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(server, port, context=context) as server:
            server.login(send_from, password)
            server.sendmail(send_from, send_to, text)

    if not isSsl:
        with smtplib.SMTP_SSL(server, port) as server:
            server.login(send_from, password)
            server.sendmail(send_from, send_to, text)