# import smtplib
# from datetime import datetime
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.base import MIMEBase
# from email import encoders
# from logs.logger_module import LOG
# from params import fromaddr, toaddr


# def send_email(tnga_report, gd_report, tnga_len_ual, tnga_len_una_df, tnga_len_a_df, gd_len_ual, gd_len_una_df, gd_len_a_df):
#     try:

#         msg = MIMEMultipart()

#         msg['From'] = fromaddr
#         msg['To'] = ', '.join(toaddr)
#         msg['Subject'] = f"IIoT Dashboard Report {datetime.now().date()}"

#         body = (
#             f"<div style='color:black;'>"
#             f"Please find attached the IIoT Dashboard Report generated for today.<br><br>"
#             f"<strong>TNGA Plant Summary:</strong><br>"
#             f"&emsp;- <strong>Total Logins</strong>: {tnga_len_ual} users<br>"
#             f"&emsp;- <strong>Abnormalities</strong>: {tnga_len_una_df} unassigned & {tnga_len_a_df} assigned<br>"
#             f"<strong>GD Plant Summary:</strong><br>"
#             f"&emsp;- <strong>Total Logins</strong>: {gd_len_ual} users<br>"
#             f"&emsp;- <strong>Abnormalities</strong>: {gd_len_una_df} unassigned & {gd_len_a_df} assigned<br>"
#             f"</div>"
#         )

#         msg.attach(MIMEText(body, 'html'))

#         tnga_attachment = open(f'reports/TNGA/{tnga_report}', "rb")
#         gd_attachment = open(f'reports/GD/{gd_report}', "rb")

#         part = MIMEBase('application', 'octet-stream')
#         part.set_payload(gd_attachment.read())
#         part.set_payload(tnga_attachment.read())
#         encoders.encode_base64(part)
#         part.add_header('Content-Disposition', "attachment; filename= %s" % tnga_report)
#         part.add_header('Content-Disposition', "attachment; filename= %s" % gd_report)

#         msg.attach(part)

#         # server = smtplib.SMTP('smtp.office365.com', 587)
#         server = smtplib.SMTP('smtp.gmail.com', 587)
#         server.starttls()
#         # server.login(fromaddr, "XTk6LHPj")
#         server.login(fromaddr, "ffxukqwnjameubem")
#         text = msg.as_string()
#         server.sendmail(fromaddr, toaddr, text)
#         server.quit()

#     except Exception as e:
#         LOG.error(e)






import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pony.orm import db_session, select

from logs.logger_module import LOG
from params import fromaddr


def get_email_recipients(db):
    """Query the EmailUser table to get all email addresses."""
    try:
        with db_session:
            email_users = select(u.email_id for u in db.EmailUser)[:]
            recipients = list(email_users) if email_users else []
            LOG.info(f"Fetched {len(recipients)} email recipients from EmailUser table")
            if recipients:
                LOG.info(f"Email recipients: {', '.join(recipients)}")
            return recipients
    except Exception as e:
        LOG.error(f"Error fetching email recipients: {e}")
        return []


def send_email(
        tnga_report,
        gd_report,
        tnga_len_ual,
        tnga_len_una_df,
        tnga_len_a_df,
        gd_len_ual,
        gd_len_una_df,
        gd_len_a_df,
        db):
    try:
        LOG.info("Starting email sending process")

        # Dynamic recipient fetching (commented out)
        # toaddr = get_email_recipients(db)

        # if not toaddr:
        #     LOG.warning("No email recipients found in EmailUser table - email will not be sent")
        #     return

        # Hardcoded recipient
        toaddr = ["gokulravi925@gmail.com"]

        LOG.info(f"Email will be sent to {len(toaddr)} recipients")

        msg = MIMEMultipart()

        msg['From'] = fromaddr
        msg['To'] = ', '.join(toaddr)
        msg['Subject'] = f"IIoT Dashboard Report {datetime.now().date()}"
        LOG.info(f"Email subject: {msg['Subject']}")

        body = (
            f"<div style='color:black;'>"
            f"Please find attached the IIoT Dashboard Report generated for today.<br><br>"
            f"<strong>TNGA Plant Summary:</strong><br>"
            f"&emsp;- <strong>Total Logins</strong>: {tnga_len_ual} users<br>"
            f"&emsp;- <strong>Abnormalities</strong>: "
            f"{tnga_len_una_df} unassigned & "
            f"{tnga_len_a_df} assigned<br>"
            f"<strong>GD Plant Summary:</strong><br>"
            f"&emsp;- <strong>Total Logins</strong>: {gd_len_ual} users<br>"
            f"&emsp;- <strong>Abnormalities</strong>: "
            f"{gd_len_una_df} unassigned & "
            f"{gd_len_a_df} assigned<br>"
            f"</div>"
        )

        msg.attach(MIMEText(body, 'html'))

        # Attach TNGA report
        with open(f'reports/TNGA/{tnga_report}', "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())

        encoders.encode_base64(part)

        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{tnga_report}"'
        )

        msg.attach(part)

        # Attach GD report
        with open(f'reports/GD/{gd_report}', "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())

        encoders.encode_base64(part)

        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{gd_report}"'
        )

        msg.attach(part)

        LOG.info("Connecting to SMTP server: smtp.office365.com:587")
        try:
            server = smtplib.SMTP('smtp.office365.com', 587, timeout=30)
            server.set_debuglevel(1)  # Enable debug logging
            LOG.info("SMTP server connected successfully")
        except Exception as e:
            LOG.error(f"Failed to connect to SMTP server: {e}")
            raise

        LOG.info("Starting TLS encryption")
        try:
            server.starttls()
            LOG.info("TLS encryption started successfully")
        except Exception as e:
            LOG.error(f"Failed to start TLS: {e}")
            server.quit()
            raise

        LOG.info("Authenticating with SMTP server")
        try:
            server.login(
                fromaddr,
                "xmIlU97F"
                # "ffxukqwnjameubem"
            )
            LOG.info("SMTP authentication successful")
        except Exception as e:
            LOG.error(f"SMTP authentication failed: {e}")
            server.quit()
            raise

        text = msg.as_string()

        LOG.info("Sending email...")
        try:
            server.sendmail(
                fromaddr,
                toaddr,
                text
            )
            LOG.info("Email sent successfully via SMTP")
        except Exception as e:
            LOG.error(f"Failed to send email: {e}")
            server.quit()
            raise

        server.quit()
        LOG.info("SMTP connection closed")

    except Exception as e:
        LOG.error(e)
        print("Email Error:", e)