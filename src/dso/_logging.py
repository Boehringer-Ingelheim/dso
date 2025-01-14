from logging import Formatter, getLogger

from rich.console import Console
from rich.logging import RichHandler

console_stderr = Console(stderr=True)
console = Console(stderr=False)
log = getLogger("dso")
log.setLevel("INFO")
handler = RichHandler(markup=True, console=console_stderr, show_path=False, show_time=True)
handler.setFormatter(Formatter("%(message)s"))
log.addHandler(handler)
