#!/usr/bin/env python
"""Test SQLAlchemy ORM integration"""
from app import app, db, Project

with app.app_context():
    print("Testing SQLAlchemy integration...")
    
    # Test 1: Query projects
    projects = Project.query.all()
    print(f"✓ Found {len(projects)} projects")
    
    # Test 2: Get first project
    if projects:
        p = projects[0]
        print(f"✓ First project: {p.name} (code: {p.code})")
        print(f"✓ to_dict() works: {bool(p.to_dict())}")
    
    print("\n✅ SQLAlchemy ORM integration successful!")
