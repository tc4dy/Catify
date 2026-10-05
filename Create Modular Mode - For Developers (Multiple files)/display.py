from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.columns import Columns

CONSOLE = Console()

STATUS_OK = "[green]OK[/green]"
STATUS_NO_EXIF = "[yellow]NO EXIF[/yellow]"
STATUS_ERROR = "[red]ERROR[/red]"
STATUS_DUP = "[magenta]DUPLICATE[/magenta]"


def print_banner(banner: str, version: str):
    CONSOLE.print(Panel(
        f"[bold cyan]{banner}[/bold cyan]\n"
        f"[bold white]Catify[/bold white] [dim]v{version}[/dim]  —  "
        f"[italic]EXIF Metadata Tool | @tc4dy[/italic]",
        border_style="cyan",
        expand=False,
    ))


def print_rich_table(records: list):
    CONSOLE.print()

    stats_ok = sum(1 for r in records if r["status"] == "ok")
    stats_noexif = sum(1 for r in records if r["status"] == "no_exif")
    stats_err = sum(1 for r in records if r["status"] == "error")
    stats_dup = sum(1 for r in records if r["is_duplicate"])
    stats_gps = sum(1 for r in records if r["gps"])
    stats_thumb = sum(1 for r in records if r["thumbnail"])

    summary = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    summary.add_column(style="dim")
    summary.add_column(style="bold")
    summary.add_row("Total files", str(len(records)))
    summary.add_row("EXIF OK", f"[green]{stats_ok}[/green]")
    summary.add_row("No EXIF", f"[yellow]{stats_noexif}[/yellow]")
    summary.add_row("Error", f"[red]{stats_err}[/red]")
    summary.add_row("Duplicate", f"[magenta]{stats_dup}[/magenta]")
    summary.add_row("With GPS", f"[cyan]{stats_gps}[/cyan]")
    summary.add_row("Thumbnail", f"[blue]{stats_thumb}[/blue]")

    CONSOLE.print(Panel(summary, title="[bold white]Summary[/bold white]", border_style="white", expand=False))
    CONSOLE.print()

    for rec in records:
        status_tag = {
            "ok": STATUS_OK,
            "no_exif": STATUS_NO_EXIF,
            "error": STATUS_ERROR,
        }.get(rec["status"], STATUS_ERROR)

        dup_tag = f"  {STATUS_DUP}" if rec["is_duplicate"] else ""

        header = Table.grid(padding=(0, 1))
        header.add_column(style="bold white", min_width=30)
        header.add_column()
        header.add_row(f"[bold cyan]{rec['file']}[/bold cyan]", f"{status_tag}{dup_tag}")
        header.add_row(f"[dim]{rec['path']}[/dim]", "")
        header.add_row(f"Size: [white]{rec['size']}[/white]  Date: [white]{rec['mtime']}[/white]", "")
        header.add_row(f"[dim]SHA256: {rec['sha256'][:16]}…[/dim]", "")

        if rec["is_duplicate"] and rec["duplicate_of"]:
            header.add_row(f"[magenta]Same file: {rec['duplicate_of']}[/magenta]", "")

        if rec["gps"]:
            g = rec["gps"]
            header.add_row(
                f"[cyan]GPS: {g['lat']}, {g['lon']}[/cyan]  "
                f"[link={g['google_maps']}][underline]Google Maps[/underline][/link]  "
                f"[link={g['openstreetmap']}][underline]OSM[/underline][/link]",
                "",
            )

        if rec["thumbnail"]:
            header.add_row(f"[blue]Thumbnail: {rec['thumbnail']}[/blue]", "")

        inner_panels = [Panel(header, expand=True, border_style="dim")]

        if rec["status"] == "ok" and rec["exif"]:
            exif_table = Table(
                box=box.SIMPLE_HEAD,
                show_header=True,
                header_style="bold magenta",
                padding=(0, 1),
                expand=True,
            )
            exif_table.add_column("Tag", style="cyan", min_width=35, no_wrap=True)
            exif_table.add_column("Value", style="white", overflow="fold")
            for tag, val in sorted(rec["exif"].items()):
                clean_tag = tag.replace("EXIF ", "").replace("Image ", "").replace("GPS ", "GPS ")
                exif_table.add_row(clean_tag, val)
            inner_panels.append(Panel(exif_table, title="[bold]EXIF[/bold]", border_style="dim"))

        CONSOLE.print(Panel(
            Columns(inner_panels, equal=False, expand=True),
            border_style="cyan",
            padding=(0, 1),
        ))
        CONSOLE.print()