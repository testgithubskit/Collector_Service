import re

with open('g:/GOKUL/TOYOTA/tiei_reporter/collectors/tiei_reporter/email_sender.py', 'r') as f:
    content = f.read()

# Update function signature
old_sig = '''def send_email(
        tnga_report,
        gd_report,
        tnga_len_ual,
        tnga_len_una_df,
        tnga_len_a_df,
        gd_len_ual,
        gd_len_una_df,
        gd_len_a_df,
        db):'''

new_sig = '''def send_email(
        tnga_report,
        gd_report,
        tnga_len_ual,
        tnga_len_una_df,
        tnga_len_a_df,
        tnga_warning_count,
        tnga_critical_count,
        tnga_disconnected_machines,
        gd_len_ual,
        gd_len_una_df,
        gd_len_a_df,
        gd_warning_count,
        gd_critical_count,
        gd_disconnected_machines,
        db):'''

content = content.replace(old_sig, new_sig)

# Update email body
old_body = '''        body = (
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
        )'''

new_body = '''        body = (
            f"<div style='color:black;'>"
            f"Please find attached the IIoT Dashboard Report generated for today.<br><br>"
            f"<strong>TNGA Plant Summary:</strong><br>"
            f"&emsp;- <strong>Total Logins</strong>: {tnga_len_ual} users<br>"
            f"&emsp;- <strong>Abnormalities</strong>: "
            f"{tnga_len_una_df} unassigned & "
            f"{tnga_len_a_df} assigned<br>"
            f"&emsp;- <strong>Abnormalities details</strong>: {tnga_warning_count} Warning & {tnga_critical_count} Critical<br>"
            f"&emsp;- <strong>Disconnected machine</strong>: {tnga_disconnected_machines}<br>"
            f"&emsp;- <strong>Dashboard link</strong>: <a href='http://10.82.126.25:3051/tiei_dynamic'>Manufacturing-Information-System — Dashboard</a><br><br>"
            f"<strong>GD Plant Summary:</strong><br>"
            f"&emsp;- <strong>Total Logins</strong>: {gd_len_ual} users<br>"
            f"&emsp;- <strong>Abnormalities</strong>: "
            f"{gd_len_una_df} unassigned & "
            f"{gd_len_a_df} assigned<br>"
            f"&emsp;- <strong>Abnormalities details</strong>: {gd_warning_count} Warning & {gd_critical_count} Critical<br>"
            f"&emsp;- <strong>Disconnected machine</strong>: {gd_disconnected_machines}<br>"
            f"&emsp;- <strong>Dashboard link</strong>: <a href='http://10.82.126.25:3051/tiei_dynamic'>Manufacturing-Information-System — Dashboard</a><br>"
            f"</div>"
        )'''

content = content.replace(old_body, new_body)

with open('g:/GOKUL/TOYOTA/tiei_reporter/collectors/tiei_reporter/email_sender.py', 'w') as f:
    f.write(content)

print('Email sender updated successfully')
