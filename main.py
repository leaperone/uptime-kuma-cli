import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from uptime_kuma_api import UptimeKumaApi, MonitorType

app = typer.Typer(help="Uptime Kuma CLI - manage monitors from the command line")
console = Console()

MONITOR_TYPES = {
    "http": MonitorType.HTTP,
    "port": MonitorType.PORT,
    "ping": MonitorType.PING,
    "dns": MonitorType.DNS,
    "keyword": MonitorType.KEYWORD,
    "push": MonitorType.PUSH,
    "docker": MonitorType.DOCKER,
    "mqtt": MonitorType.MQTT,
    "postgres": MonitorType.POSTGRES,
    "mysql": MonitorType.MYSQL,
    "mongodb": MonitorType.MONGODB,
    "redis": MonitorType.REDIS,
}

STATUS_TEXT = {
    0: "[red]DOWN[/red]",
    1: "[green]UP[/green]",
    2: "[yellow]PENDING[/yellow]",
    3: "[blue]MAINT[/blue]",
}


def connect(ctx: typer.Context) -> UptimeKumaApi:
    cfg = ctx.ensure_object(dict)
    url = cfg.get("url")
    if not url:
        console.print("[red]Error: URL is required. Set KUMA_URL or use --url.[/red]")
        raise typer.Exit(1)
    try:
        api = UptimeKumaApi(url)
        username = cfg.get("username")
        password = cfg.get("password")
        if username and password:
            api.login(username, password)
        else:
            api.login()
        return api
    except Exception as e:
        console.print(f"[red]Failed to connect: {e}[/red]")
        raise typer.Exit(1)


def get_status_map(api: UptimeKumaApi) -> dict[int, int]:
    """Build monitor_id -> latest status map from heartbeat data."""
    try:
        heartbeats = api.get_heartbeats()
        status_map = {}
        if isinstance(heartbeats, dict):
            for mid_str, hb_data in heartbeats.items():
                mid = int(mid_str)
                hb_list = hb_data if isinstance(hb_data, list) else hb_data.get("data", [])
                if hb_list:
                    status_map[mid] = hb_list[-1].get("status", -1)
        elif isinstance(heartbeats, list):
            for item in heartbeats:
                mid = item.get("monitorID", item.get("id"))
                data = item.get("data", [])
                if mid and data:
                    status_map[int(mid)] = data[-1].get("status", -1)
        return status_map
    except Exception:
        return {}


@app.callback()
def callback(
    ctx: typer.Context,
    url: Optional[str] = typer.Option(None, "--url", envvar="KUMA_URL", help="Uptime Kuma server URL"),
    username: Optional[str] = typer.Option(None, "--username", "-u", envvar="KUMA_USERNAME", help="Username"),
    password: Optional[str] = typer.Option(None, "--password", "-p", envvar="KUMA_PASSWORD", help="Password"),
):
    """Uptime Kuma CLI - manage monitors from the command line.

    Set KUMA_URL, KUMA_USERNAME, KUMA_PASSWORD environment variables or use --url, --username, --password options.
    """
    ctx.ensure_object(dict)
    ctx.obj["url"] = url
    ctx.obj["username"] = username
    ctx.obj["password"] = password


@app.command()
def info(ctx: typer.Context):
    """Show server info."""
    api = connect(ctx)
    try:
        data = api.info()
        console.print(f"Version: {data.get('version', 'N/A')}")
        console.print(f"Latency: {data.get('latency', 'N/A')}ms")
    finally:
        api.disconnect()


@app.command("list")
def list_monitors(ctx: typer.Context):
    """List all monitors."""
    api = connect(ctx)
    try:
        monitors = api.get_monitors()
        if not monitors:
            console.print("No monitors found.")
            return

        status_map = get_status_map(api)

        table = Table()
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Name", style="bold")
        table.add_column("Type")
        table.add_column("Target")
        table.add_column("Status")
        table.add_column("Interval", justify="right")

        for m in sorted(monitors, key=lambda x: x.get("id", 0)):
            mid = m.get("id")
            mtype = m.get("type", "")
            target = m.get("url") or m.get("hostname") or ""
            if m.get("port"):
                target += f":{m['port']}"

            if not m.get("active", True):
                status = "[dim]PAUSED[/dim]"
            else:
                status = STATUS_TEXT.get(status_map.get(mid, -1), "[dim]--[/dim]")

            interval = f"{m.get('interval', '?')}s"
            table.add_row(str(mid), m.get("name", ""), str(mtype), target, status, interval)

        console.print(table)
    finally:
        api.disconnect()


@app.command()
def get(ctx: typer.Context, monitor_id: int = typer.Argument(help="Monitor ID")):
    """Get monitor details."""
    api = connect(ctx)
    try:
        m = api.get_monitor(monitor_id)
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="bold cyan")
        table.add_column("Value")

        fields = [
            ("ID", "id"), ("Name", "name"), ("Type", "type"),
            ("URL", "url"), ("Hostname", "hostname"), ("Port", "port"),
            ("Active", "active"), ("Interval", "interval"),
            ("Retry Interval", "retryInterval"), ("Max Retries", "maxretries"),
            ("Description", "description"), ("Keyword", "keyword"),
            ("Accepted Codes", "accepted_statuscodes"),
        ]
        for label, key in fields:
            val = m.get(key)
            if val is not None and val != "":
                table.add_row(label, str(val))

        console.print(table)
    finally:
        api.disconnect()


@app.command()
def add(
    ctx: typer.Context,
    monitor_type: str = typer.Argument(help="Monitor type (http, ping, port, dns, keyword, push, ...)"),
    name: str = typer.Argument(help="Monitor name"),
    target: str = typer.Argument(help="URL (for http/keyword) or hostname (for ping/port/dns)"),
    port: Optional[int] = typer.Option(None, "--port", help="Port number (for port/dns type)"),
    interval: int = typer.Option(60, "--interval", "-i", help="Check interval in seconds"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="Keyword to search (for keyword type)"),
    dns_type: str = typer.Option("A", "--dns-type", help="DNS record type (for dns type)"),
):
    """Add a new monitor."""
    if monitor_type not in MONITOR_TYPES:
        console.print(f"[red]Unknown type '{monitor_type}'. Available: {', '.join(MONITOR_TYPES)}[/red]")
        raise typer.Exit(1)

    api = connect(ctx)
    try:
        kwargs: dict = {
            "type": MONITOR_TYPES[monitor_type],
            "name": name,
            "interval": interval,
        }

        if monitor_type in ("http", "keyword", "mqtt"):
            kwargs["url"] = target
        elif monitor_type in ("ping", "port", "dns"):
            kwargs["hostname"] = target
        else:
            kwargs["url"] = target

        if port is not None:
            kwargs["port"] = port
        if monitor_type == "keyword" and keyword:
            kwargs["keyword"] = keyword
        if monitor_type == "dns":
            kwargs["dns_resolve_type"] = dns_type
            kwargs["port"] = port or 53
            kwargs["dns_resolve_server"] = "1.1.1.1"

        result = api.add_monitor(**kwargs)
        console.print(f"[green]Monitor added (ID: {result['monitorID']})[/green]")
    finally:
        api.disconnect()


@app.command()
def edit(
    ctx: typer.Context,
    monitor_id: int = typer.Argument(help="Monitor ID"),
    name: Optional[str] = typer.Option(None, "--name", help="New name"),
    url: Optional[str] = typer.Option(None, "--target", help="New URL or hostname"),
    interval: Optional[int] = typer.Option(None, "--interval", "-i", help="New interval in seconds"),
):
    """Edit a monitor."""
    api = connect(ctx)
    try:
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if url is not None:
            kwargs["url"] = url
        if interval is not None:
            kwargs["interval"] = interval

        if not kwargs:
            console.print("[yellow]No changes specified.[/yellow]")
            return

        api.edit_monitor(monitor_id, **kwargs)
        console.print(f"[green]Monitor {monitor_id} updated.[/green]")
    finally:
        api.disconnect()


@app.command()
def delete(
    ctx: typer.Context,
    monitor_id: int = typer.Argument(help="Monitor ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a monitor."""
    if not yes:
        typer.confirm(f"Delete monitor {monitor_id}?", abort=True)

    api = connect(ctx)
    try:
        api.delete_monitor(monitor_id)
        console.print(f"[green]Monitor {monitor_id} deleted.[/green]")
    finally:
        api.disconnect()


@app.command()
def pause(ctx: typer.Context, monitor_id: int = typer.Argument(help="Monitor ID")):
    """Pause a monitor."""
    api = connect(ctx)
    try:
        api.pause_monitor(monitor_id)
        console.print(f"[green]Monitor {monitor_id} paused.[/green]")
    finally:
        api.disconnect()


@app.command()
def resume(ctx: typer.Context, monitor_id: int = typer.Argument(help="Monitor ID")):
    """Resume a monitor."""
    api = connect(ctx)
    try:
        api.resume_monitor(monitor_id)
        console.print(f"[green]Monitor {monitor_id} resumed.[/green]")
    finally:
        api.disconnect()


if __name__ == "__main__":
    app()
