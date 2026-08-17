"""Seed data: Rogerio's sections + companies from the wireframe."""
from sqlalchemy.orm import Session

from .models import Board, Task


def seed(db: Session) -> None:
    if db.query(Board).first():
        return  # already seeded

    # Sections (top-level)
    personal = Board(name="Personal Projects", kind="section", color="#3b82f6", sort_order=0)
    rc = Board(name="RC Exteriors", kind="section", color="#f97316", sort_order=1)
    clients = Board(name="Clients", kind="section", color="#22c55e", sort_order=2)
    ladybug = Board(name="Ladybug", kind="section", color="#a855f7", sort_order=3)
    db.add_all([personal, rc, clients, ladybug])
    db.flush()

    # Personal Projects companies
    personal_companies = [
        ("eyegenerate.com", "#60a5fa"),
        ("5bell.com", "#93c5fd"),
        ("tienda-guatemala.com", "#3b82f6"),
        ("Other", "#2563eb"),
        ("Auction Buy & Sell Cars", "#1d4ed8"),
        ("Open Cowboys Store", "#1e40af"),
    ]
    for i, (name, color) in enumerate(personal_companies):
        db.add(Board(name=name, parent_id=personal.id, kind="company", color=color, sort_order=i))

    # RC Exteriors projects
    rc_projects = [
        ("Manage Projects", "#fb923c"),
        ("Sales Team", "#f97316"),
        ("Marketing Team", "#ea580c"),
        ("Investigate", "#c2410c"),
    ]
    for i, (name, color) in enumerate(rc_projects):
        db.add(Board(name=name, parent_id=rc.id, kind="project", color=color, sort_order=i))

    # Clients (placeholder top-level examples)
    db.add(Board(name="Fern & Juniper (Corstone)", parent_id=clients.id, kind="company", color="#4ade80", sort_order=0))
    db.add(Board(name="Bothell Lot P (VCC)", parent_id=clients.id, kind="company", color="#22c55e", sort_order=1))

    # Ladybug companies
    db.add(Board(name="LadyBug Fresh Spaces", parent_id=ladybug.id, kind="company", color="#c084fc", sort_order=0))
    db.add(Board(name="Ladybug Cleaning Academy", parent_id=ladybug.id, kind="company", color="#a855f7", sort_order=1))
    db.add(Board(name="Quality Cleaning Co", parent_id=ladybug.id, kind="company", color="#9333ea", sort_order=2))

    db.commit()
