import pitschi.config as config
import requests, json

def send_teams_warning(title, message):
    """
    send a warning
    """
    send_teams_notification("Warning", title, message)
    
def send_teams_error(title, message):
    """
    send an error
    """
    send_teams_notification("Error", title, message)


def send_teams_notification(type, title, message):
    """
    send a notification to teams
    """
    url = f"{config.get('miscs', 'teams_webhook')}"
    if type == "Error":
        themeColor = "c60000"
    elif type == "Warning":
        themeColor = "c6c600"
    else:
        themeColor = "0078D7"
    payload = {
                "@context": "https://schema.org/extensions",
                "@type": "MessageCard",
                "themeColor": themeColor,
                "title": f"[{type}] {title}",
                "text": message,
            }
    requests.request("POST", url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))