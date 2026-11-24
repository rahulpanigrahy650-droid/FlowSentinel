"""Create sample incidents and run the full workflow on them:  python -m scripts.seed_demo"""
from app.db import SessionLocal, init_db
from app.schemas import IncidentCreate
from app.services import incident_service as svc
from app.services.ingestion import seed_knowledge_base
from app.services.runtime import get_runtime, make_store

SAMPLES = [
    ("Production database primary not responding", "All users get errors on the customer portal. Postgres primary stopped accepting connections at 09:12, connection pool is exhausted.", "ops-bot"),
    ("VPN disconnects every 10 minutes", "Working from home since Monday. GlobalProtect VPN drops roughly every 10 minutes and I have to reconnect.", "priya.s"),
    ("Clicked a link in a suspicious email", "I received an invoice email from an unknown sender, clicked the link and typed my Microsoft password. Please advise.", "daniel.k"),
    ("Disk full on build server", "No space left on device on ci-runner-3. 40 developers cannot run pipelines, deploys are failing.", "sre-oncall"),
    ("Locked out of my account after password change", "I changed my password yesterday and now my account is locked out on my phone and laptop.", "maria.l"),
    ("Pod keeps restarting in CrashLoopBackOff", "The payments-api pod in the production cluster is in CrashLoopBackOff since the last deployment.", "dev-team"),
    ("Outlook will not sync new email", "Outlook shows 'Disconnected' and new email stopped arriving on my laptop this morning.", "tom.h"),
    ("Printer on floor 3 shows paper jam", "The floor 3 printer reports a paper jam but there is no paper stuck.", "reception"),
    ("SSL certificate expired on intranet", "Browsers show a certificate expired warning on the intranet site for all employees.", "web-admin"),
    ("How do I request a new software license?", "Not urgent - I would like to install Figma, how to request a license?", "lena.r"),
    ("Website returns HTTP 500 on checkout", "Customers report a 500 error when they press Pay on the checkout page since the 14:00 release.", "support"),
    ("Slow DNS lookups in the Berlin office", "Internal hostnames take 5-10 seconds to resolve in the Berlin office, other offices are fine.", "it-berlin"),
]

if __name__ == "__main__":
    init_db()
    with SessionLocal() as db:
        seed_knowledge_base(db, make_store(db), get_runtime().settings.kb_dir)
        for title, desc, who in SAMPLES:
            inc = svc.create_incident(db, IncidentCreate(title=title, description=desc, reporter=who))
            svc.analyze_incident(db, inc)
            print(f"#{inc.id:<3} {inc.severity:<9} {inc.category:<16} {inc.route:<10} {inc.title}")
