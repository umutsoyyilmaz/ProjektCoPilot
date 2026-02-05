#!/usr/bin/env python
"""Minimal test - only Project model"""
from app import app, db
from models import Project

with app.app_context():
    print("Testing Projects ORM migration...")
    
    # Test query
    try:
        projects = db.session.query(Project).all()
        print(f"✓ Query successful: Found {len(projects)} projects")
        
        if projects:
            p = projects[0]
            print(f"✓ First project: {p.name} (ID: {p.id})")
            print(f"✓ to_dict() works: {p.to_dict()['project_name']}")
        
        print("\n✅ Projects ORM integration successful!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
