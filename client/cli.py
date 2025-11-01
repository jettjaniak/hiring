#!/usr/bin/env python3
"""
CLI interface for hiring process client
"""
import click
import sys
from datetime import datetime
from tabulate import tabulate
from config import Config
from database import Database
from encryption import EncryptionManager
from sync import SyncEngine
from migrations import MigrationManager, KeyRotationManager
import models


class ClientContext:
    """Shared context for CLI commands"""

    def __init__(self, data_dir=None):
        self.config = Config(config_dir=data_dir)
        self.db = None
        self.sync = None
        self.encryption = None

    def init(self):
        """Initialize client"""
        if not self.config.is_initialized():
            click.echo("Client not initialized. Run 'init' command first.")
            sys.exit(1)

        self.encryption = EncryptionManager(self.config.encryption_key)
        self.db = Database(str(self.config.db_file))
        self.db.init_db()
        self.sync = SyncEngine(self.config.server_url, self.encryption)

        # Verify key with server
        self._verify_key()

    def _verify_key(self):
        """Verify encryption key matches server's canary"""
        import requests
        try:
            response = requests.get(f"{self.config.server_url}/key-verification")
            if response.status_code == 200:
                data = response.json()
                encrypted_canary = data['encrypted_canary'].encode('latin1')

                if not self.encryption.verify_canary(encrypted_canary):
                    click.echo("ERROR: Wrong encryption key!", err=True)
                    click.echo("Your key does not match the server's key.", err=True)
                    click.echo("Please reinitialize with the correct key.", err=True)
                    sys.exit(1)
        except requests.exceptions.RequestException:
            # Ignore network errors during verification - assume key is correct
            pass


pass_context = click.make_pass_decorator(ClientContext, ensure=True)


@click.group()
@click.option('--data-dir', default=None,
              help='Data directory for client files (default: ~/.hiring-client)')
@click.pass_context
def cli(ctx, data_dir):
    """Hiring Process Management Client"""
    ctx.obj = ClientContext(data_dir=data_dir)


@cli.command()
@click.option('--key', help='Encryption key (passphrase). If not provided, will prompt.')
@click.option('--server', default='http://localhost:8000/api',
              help='Server URL')
@pass_context
def init(ctx, key, server):
    """Initialize the client with encryption key"""
    # Prompt for key if not provided
    if not key:
        key = click.prompt('Encryption key', hide_input=True)
        key_confirm = click.prompt('Confirm encryption key', hide_input=True)
        if key != key_confirm:
            click.echo("Keys do not match", err=True)
            sys.exit(1)
    ctx.config.encryption_key = key
    ctx.config.server_url = server
    ctx.config.schema_version = 1

    # Initialize database
    ctx.encryption = EncryptionManager(key)
    db = Database(str(ctx.config.db_file))
    db.init_db()

    # Verify key with server
    click.echo("Verifying encryption key with server...")
    import requests
    try:
        # Check if server has a canary
        response = requests.get(f"{server}/key-verification")

        if response.status_code == 404:
            # No canary exists, create one
            click.echo("  No key verification found on server. Initializing...")
            canary = ctx.encryption.create_canary()
            create_response = requests.post(
                f"{server}/key-verification",
                json={"encrypted_canary": canary.decode('latin1')}
            )
            create_response.raise_for_status()
            click.echo("  ✓ Key verification initialized on server")
        elif response.status_code == 200:
            # Canary exists, verify it
            click.echo("  Verifying against existing key...")
            data = response.json()
            encrypted_canary = data['encrypted_canary'].encode('latin1')

            if not ctx.encryption.verify_canary(encrypted_canary):
                click.echo("ERROR: Wrong encryption key!", err=True)
                click.echo("This key does not match the key used to initialize the server.", err=True)
                click.echo("Please use the correct encryption key.", err=True)
                sys.exit(1)

            click.echo("  ✓ Key verified successfully")
        else:
            response.raise_for_status()

    except requests.exceptions.RequestException as e:
        click.echo(f"WARNING: Could not verify key with server: {e}", err=True)
        click.echo("Continuing anyway, but sync may fail if wrong key is used.", err=True)

    click.echo("\n✓ Client initialized successfully")
    click.echo(f"  Database: {ctx.config.db_file}")
    click.echo(f"  Server: {server}")


@cli.command()
@pass_context
def sync(ctx):
    """Sync with server"""
    ctx.init()

    session = ctx.db.get_session()
    try:
        last_sync = ctx.config.last_sync
        if last_sync:
            since = datetime.fromisoformat(last_sync)
            click.echo(f"Syncing changes since {since.strftime('%Y-%m-%d %H:%M:%S')}...")
        else:
            since = datetime(2000, 1, 1)
            click.echo("Performing initial sync...")

        # Full sync: pull first (to get latest versions), then push
        result = ctx.sync.full_sync(session, since=since)

        # Report results
        push_stats = result['push']
        pull_stats = result['pull']

        if push_stats['candidates_pushed'] > 0 or push_stats['tasks_pushed'] > 0:
            click.echo(f"📤 Pushed: {push_stats['candidates_pushed']} candidates, {push_stats['tasks_pushed']} tasks")

        if pull_stats['candidates_new'] > 0 or pull_stats['candidates_updated'] > 0:
            click.echo(f"📥 Pulled: {pull_stats['candidates_new']} new, {pull_stats['candidates_updated']} updated candidates")

        if push_stats['candidates_failed'] > 0 or push_stats['tasks_failed'] > 0:
            click.echo(f"⚠️  Failures: {push_stats['candidates_failed']} candidates, {push_stats['tasks_failed']} tasks", err=True)
            for failed in push_stats['failed_items'][:3]:  # Show first 3 failures
                click.echo(f"   {failed['type']} {failed['id']}: {failed['error']}", err=True)

        ctx.config.last_sync = result['sync_timestamp']
        click.echo(f"✓ Sync complete at {result['sync_timestamp']}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        session.close()


@cli.command()
@pass_context
def migrate(ctx):
    """Run schema migrations"""
    ctx.init()

    session = ctx.db.get_session()
    try:
        migration_mgr = MigrationManager(ctx.config, session, ctx.sync)

        if not migration_mgr.needs_migration():
            click.echo("Already at latest schema version")
            return

        migration_mgr.migrate()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        session.close()


@cli.command()
@click.option('--old-key', prompt=True, hide_input=True, help='Current encryption key')
@click.option('--new-key', prompt=True, hide_input=True, confirmation_prompt=True,
              help='New encryption key')
@pass_context
def rotate_key(ctx, old_key, new_key):
    """Rotate encryption key"""
    if not ctx.config.is_initialized():
        click.echo("Client not initialized", err=True)
        sys.exit(1)

    # Verify old key
    if ctx.config.encryption_key != old_key:
        click.echo("Old key does not match current key", err=True)
        sys.exit(1)

    ctx.init()

    session = ctx.db.get_session()
    try:
        rotation_mgr = KeyRotationManager(ctx.config, session, ctx.sync)
        rotation_mgr.rotate_key(old_key, new_key)

        click.echo("✓ Encryption key rotated successfully")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        session.close()


@cli.command()
@pass_context
def status(ctx):
    """Show client status"""
    if not ctx.config.is_initialized():
        click.echo("Status: Not initialized")
        click.echo("Run 'init' command to get started")
        return

    click.echo("Status: Initialized")
    click.echo(f"  Server: {ctx.config.server_url}")
    click.echo(f"  Database: {ctx.config.db_file}")
    click.echo(f"  Schema version: {ctx.config.schema_version}")

    if ctx.config.last_sync:
        last_sync = datetime.fromisoformat(ctx.config.last_sync)
        click.echo(f"  Last sync: {last_sync.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        click.echo(f"  Last sync: Never")

    ctx.init()
    session = ctx.db.get_session()
    try:
        candidate_count = session.query(models.Candidate).count()
        click.echo(f"  Candidates: {candidate_count}")
    finally:
        session.close()


if __name__ == '__main__':
    cli()
