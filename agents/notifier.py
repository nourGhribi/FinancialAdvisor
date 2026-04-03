"""
Notifier — renders the Jinja2 HTML template and sends it via Gmail SMTP.
"""
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pytz
from jinja2 import Environment, FileSystemLoader

import config

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))


def _edition_name(hour: int) -> str:
    if hour < 10:
        return "Morning"
    if hour < 15:
        return "Midday"
    return "Evening"


def render_email(context: dict) -> str:
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz=tz)
    edition = _edition_name(now.hour)

    template = _jinja_env.get_template("briefing.html.j2")
    return template.render(
        edition=edition,
        date=now.strftime("%B %d, %Y"),
        time=now.strftime("%I:%M %p"),
        timezone=config.TIMEZONE,
        # Market data
        indices=context.get("market_data", {}).get("indices", {}),
        market_mood=context.get("market_data", {}).get("market_mood", ""),
        # Sector sentiment
        sector_sentiment=context.get("sentiment_data", {}).get("sector_sentiment", []),
        analyst_note=context.get("sentiment_data", {}).get("analyst_note", ""),
        # Reddit
        trending_tickers=context.get("reddit_data", {}).get("trending_tickers", [])[:10],
        # Risk
        risk_alerts=context.get("risk_data", {}).get("risk_alerts", []),
        # Signals
        signals=context.get("advisor_data", {}).get("signals", []),
        portfolio_notes=context.get("advisor_data", {}).get("portfolio_notes", ""),
        top_pick=context.get("advisor_data", {}).get("top_pick", ""),
        # News
        macro_headlines=context.get("news_data", {}).get("macro_headlines", []),
    )


def send_email(html_body: str, subject: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.RECIPIENT_EMAIL

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.GMAIL_ADDRESS, config.RECIPIENT_EMAIL, msg.as_string())


def run(context: dict) -> dict:
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz=tz)
    edition = _edition_name(now.hour)

    html = render_email(context)
    subject = f"[{edition} Briefing] Financial Intelligence — {now.strftime('%b %d, %Y')}"
    send_email(html, subject)

    return {"status": "sent", "subject": subject, "sent_at": now.isoformat()}
