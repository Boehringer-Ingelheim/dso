from logging import basicConfig, getLogger

from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install

console_stderr = Console(stderr=True)
console = Console(stderr=False)
log = getLogger("dso")
basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[RichHandler(markup=True, console=console_stderr, show_path=False, show_time=True)],
)
install(show_locals=True)
