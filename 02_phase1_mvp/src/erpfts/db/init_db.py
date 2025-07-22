"""
Database initialization utilities for ERPFTS Phase1 MVP

Provides functions to create tables, initialize data, and manage
database schema operations.
"""

from sqlalchemy.orm import Session
from loguru import logger

from ..models.database import Base, User, KnowledgeSource
from .session import engine, get_db_session
from ..core.config import settings


def create_tables():
    """Create all database tables."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_tables():
    """Drop all database tables."""
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("Database tables dropped successfully")


def init_default_user(db: Session):
    """Create default admin user if none exists."""
    existing_admin = db.query(User).filter(User.is_admin == True).first()
    if not existing_admin:
        logger.info("Creating default admin user...")
        
        # Import here to avoid circular import
        from ..utils.auth import get_password_hash
        
        default_user = User(
            username="admin",
            email="admin@erpfts.local",
            hashed_password=get_password_hash("admin123"),
            full_name="ERPFTS Administrator",
            is_admin=True,
            is_active=True,
        )
        
        db.add(default_user)
        db.commit()
        logger.info("Default admin user created (username: admin, password: admin123)")
    else:
        logger.info("Admin user already exists")


def init_knowledge_sources(db: Session):
    """Initialize default knowledge sources."""
    knowledge_sources = [
        {
            "id": "pmbok",
            "name": "PMBOK Guide 7th Edition",
            "source_type": "document",
            "config": {
                "version": "7th Edition",
                "publisher": "PMI",
                "language": "english",
                "priority": 1,
            },
        },
        {
            "id": "babok",
            "name": "BABOK Guide v3.0",
            "source_type": "document",
            "config": {
                "version": "3.0",
                "publisher": "IIBA", 
                "language": "english",
                "priority": 1,
            },
        },
        {
            "id": "dmbok",
            "name": "DMBOK 2nd Edition",
            "source_type": "document",
            "config": {
                "version": "2nd Edition",
                "publisher": "DAMA",
                "language": "english",
                "priority": 2,
            },
        },
        {
            "id": "spem",
            "name": "SPEM 2.0 Specification",
            "source_type": "document",
            "config": {
                "version": "2.0",
                "publisher": "OMG",
                "language": "english",
                "priority": 3,
            },
        },
        {
            "id": "togaf",
            "name": "TOGAF 10th Edition",
            "source_type": "document",
            "config": {
                "version": "10th Edition",
                "publisher": "The Open Group",
                "language": "english",
                "priority": 2,
            },
        },
        {
            "id": "bif_blog",
            "name": "BIF Consulting Blog",
            "source_type": "blog",
            "source_url": "https://www.bif-consulting.co.jp/blog/",
            "config": {
                "language": "japanese",
                "update_frequency": "monthly",
                "priority": 3,
            },
        },
    ]
    
    for source_data in knowledge_sources:
        existing = db.query(KnowledgeSource).filter(
            KnowledgeSource.id == source_data["id"]
        ).first()
        
        if not existing:
            logger.info(f"Creating knowledge source: {source_data['name']}")
            source = KnowledgeSource(**source_data)
            db.add(source)
        else:
            logger.info(f"Knowledge source already exists: {source_data['name']}")
    
    db.commit()
    logger.info("Knowledge sources initialized")


def init_database():
    """Initialize the complete database with tables and default data."""
    logger.info("Initializing ERPFTS database...")
    
    # Ensure storage directories exist
    settings.ensure_directories()
    
    # Create tables
    create_tables()
    
    # Initialize default data
    db = get_db_session()
    try:
        init_default_user(db)
        init_knowledge_sources(db)
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def reset_database():
    """Reset the database by dropping and recreating all tables."""
    logger.warning("Resetting database - all data will be lost!")
    drop_tables()
    init_database()
    logger.info("Database reset completed")