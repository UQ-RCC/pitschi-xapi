import smtplib, ssl
from email.message import EmailMessage
from smtplib import SMTP
import pitschi.config as config
import logging, time

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(name)s] %(levelname)s : %(message)s')
logger = logging.getLogger(__name__)

def connect_smtp():
    connection = smtplib.SMTP(config.get('email', 'smtp_server'),
            config.get('email', 'smtp_port'))
    if config.get('email', 'smtp_tls', default='True').lower() == 'true':
        if config.get('email', 'smtp_server') == 'smtp.uq.edu.au':
            context=ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.set_ciphers('DEFAULT@SECLEVEL=1')
        connection.ehlo()
        if config.get('email', 'smtp_server') == 'smtp.uq.edu.au':
            connection.starttls(context=context)
        else:
            connection.starttls()
    username, passwd = config.get('email', 'username'), config.get('email', 'password')
    if username and passwd:
        connection.ehlo()
        connection.login(username, passwd)
    return connection

def send_mail(to_address, subject, contents, subtype='html', to_sender=False, cc_sender=True):
    """
    Send email
    """
    ### create connectoin first
    ### try 3 times
    if config.get('email', 'enabled', default='yes') == 'no':
        logger.info(f'send_mail to: {to_address}, subj: {subject}')
        return
    connected = False
    attempts = 0
    while not connected:
        attempts = attempts + 1
        try:
            connection = connect_smtp()
            connected = True
        except Exception as e:
            logger.error(f"Problem with create smtp connection: {str(e)}")
            if attempts < 3:
                logger.debug("Try connecting to smtp server again...")
                time.sleep(3)
            else:
                raise
    ### send the email
    try:
        email = EmailMessage()
        sender = config.get('email', 'address')
        email['Subject'] = subject
        email['From'] = sender
        if to_sender:
            email['To'] = to_address+','+sender
        else:
            email['To'] = to_address
        if cc_sender:
            email['Cc'] = sender
        email.set_content(contents, subtype=subtype)
        connection.send_message(email)
    finally:
        # close connection
        connection.close()

def main(argv):
    """
    main method
    """
    print(config.get('email', 'address'))
    print(config.get('email', 'user'))
    print(config.get('email', 'password'))
    
    you = "xxxx"
    contents = """
    <html>
        <head></head>
        <body>
            <p>Hi!<br>
            These are the following samples need to be fixed:<br>
                 <ul>
                    <li>sample 1</li>
                    <li>sample 2</li>
                    <li>sample 3</li>
                </ul> 
            </p>
        </body>
        </html>
    """
    send_mail(you, 'This is another test', contents)
if __name__ == '__main__':
    main([])    
