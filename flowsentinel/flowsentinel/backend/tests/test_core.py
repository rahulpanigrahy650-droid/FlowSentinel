import math

from app.core.chunking import chunk_markdown
from app.core.embeddings import HashingEmbeddings
from app.core.heuristics import heuristic_triage, severity_rank


def test_embeddings_are_normalised_and_deterministic():
    e = HashingEmbeddings(1024)
    v1, v2 = e.embed_query("VPN keeps disconnecting"), e.embed_query("VPN keeps disconnecting")
    assert v1 == v2
    assert math.isclose(sum(x * x for x in v1), 1.0, rel_tol=1e-6)


def test_similar_text_scores_higher_than_unrelated():
    e = HashingEmbeddings(1024)
    q = e.embed_query("vpn disconnects every ten minutes")
    near = e.embed_query("VPN frequent disconnects wifi packet loss")
    far = e.embed_query("printer paper jam toner")
    dot = lambda a, b: sum(x * y for x, y in zip(a, b))
    assert dot(q, near) > dot(q, far)


def test_chunking_keeps_heading_path_and_splits_long_sections():
    md = "# Title\n\n## Steps\n" + "\n\n".join(f"Paragraph {i} " + "word " * 80 for i in range(10))
    chunks = chunk_markdown(md, max_chars=500, overlap=50)
    assert len(chunks) > 3
    assert all(c.heading == "Title > Steps" for c in chunks)
    assert all(len(c.text) <= 800 for c in chunks)


def test_critical_incident_is_detected():
    r = heuristic_triage("Production database down", "All users cannot login, postgres primary not responding")
    assert r["category"] == "database" and r["severity"] == "critical"


def test_low_priority_request():
    r = heuristic_triage("How do I install Zoom?", "Not urgent, new starter request")
    assert r["severity"] == "low" and r["category"] == "service_request"


def test_hard_critical_keywords_force_critical():
    r = heuristic_triage("Files renamed", "Our files are encrypted files with a ransom note")
    assert r["severity"] == "critical" and severity_rank(r["severity"]) == 3
