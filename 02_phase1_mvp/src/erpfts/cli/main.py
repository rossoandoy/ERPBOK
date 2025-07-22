"""
Main CLI entry point for ERPFTS Phase1 MVP

Provides command-line interface for database initialization,
development utilities, and system administration.
"""

import click
from loguru import logger

from ..core.config import settings
from ..db.init_db import init_database, reset_database
from ..utils.file_utils import get_storage_stats


@click.group()
@click.version_option(version=settings.app_version)
def cli():
    """ERPFTS Phase1 MVP Command Line Interface"""
    pass


@cli.command()
def init_db():
    """Initialize the database with tables and default data."""
    try:
        init_database()
        click.echo("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        click.echo(f"❌ Database initialization failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--confirm", is_flag=True, help="Confirm database reset")
def reset_db(confirm):
    """Reset the database (WARNING: All data will be lost!)"""
    if not confirm:
        click.confirm(
            "This will delete all data. Are you sure?",
            abort=True
        )
    
    try:
        reset_database()
        click.echo("✅ Database reset successfully")
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        click.echo(f"❌ Database reset failed: {e}", err=True)
        raise click.Abort()


@cli.command()
def storage_stats():
    """Show storage usage statistics."""
    try:
        stats = get_storage_stats()
        
        click.echo("📊 Storage Statistics")
        click.echo("=" * 40)
        click.echo(f"Total files: {stats['total_files']:,}")
        click.echo(f"Total size: {stats['total_size_mb']:.2f} MB")
        click.echo()
        
        click.echo("Directory breakdown:")
        for dir_path, dir_stats in stats["directories"].items():
            size_mb = dir_stats["size_bytes"] / (1024 * 1024)
            click.echo(f"  {dir_path}: {dir_stats['files']} files, {size_mb:.2f} MB")
            
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        click.echo(f"❌ Failed to get storage stats: {e}", err=True)


@cli.command()
def health_check():
    """Perform system health check."""
    click.echo("🔍 System Health Check")
    click.echo("=" * 40)
    
    # Check storage directories
    try:
        settings.ensure_directories()
        click.echo("✅ Storage directories: OK")
    except Exception as e:
        click.echo(f"❌ Storage directories: {e}")
    
    # Check database connection
    try:
        from ..db.session import engine
        with engine.connect():
            pass
        click.echo("✅ Database connection: OK")
    except Exception as e:
        click.echo(f"❌ Database connection: {e}")
    
    # Check configuration
    try:
        click.echo(f"✅ Configuration loaded: {settings.app_name}")
        click.echo(f"   - Debug mode: {settings.debug}")
        click.echo(f"   - Log level: {settings.log_level}")
        click.echo(f"   - API port: {settings.api_port}")
        click.echo(f"   - UI port: {settings.ui_port}")
    except Exception as e:
        click.echo(f"❌ Configuration: {e}")


@cli.command()
def run_api():
    """Start the FastAPI server."""
    from ..api.main import run_server
    
    click.echo(f"🚀 Starting API server on {settings.api_host}:{settings.api_port}")
    run_server()


@cli.command()
def run_ui():
    """Start the Streamlit UI."""
    import subprocess
    import sys
    
    click.echo(f"🎨 Starting UI on {settings.ui_host}:{settings.ui_port}")
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "src/erpfts/ui/main.py",
        "--server.port", str(settings.ui_port),
        "--server.address", settings.ui_host,
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Failed to start UI: {e}", err=True)
    except KeyboardInterrupt:
        click.echo("\n👋 UI server stopped")


@cli.command()
def dev_server():
    """Start both API and UI servers for development."""
    import subprocess
    import sys
    import time
    from threading import Thread
    
    def run_api_server():
        from ..api.main import run_server
        run_server()
    
    def run_ui_server():
        time.sleep(2)  # Wait for API to start
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "src/erpfts/ui/main.py",
            "--server.port", str(settings.ui_port),
            "--server.address", settings.ui_host,
        ])
    
    click.echo("🚀 Starting development servers...")
    click.echo(f"   API: http://{settings.api_host}:{settings.api_port}")
    click.echo(f"   UI:  http://{settings.ui_host}:{settings.ui_port}")
    
    try:
        # Start API in background thread
        api_thread = Thread(target=run_api_server, daemon=True)
        api_thread.start()
        
        # Start UI in main thread
        run_ui_server()
        
    except KeyboardInterrupt:
        click.echo("\n👋 Development servers stopped")


def main():
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()