"""
open_terminal_f4 — atalho F4 (tecla pura) para abrir o terminal na pasta atual do Nautilus.

Dois problemas que esta extensão resolve:

1) F4 não disparava: a extensão oficial `nautilus-open-any-terminal` registra o atalho via
   `Gtk.Application.set_accels_for_action`, mecanismo que no GTK4 NÃO dispara com teclas sem
   modificador (F4 puro é aceito mas nunca acionado). Aqui contornamos anexando um
   GtkEventControllerKey na fase CAPTURE a cada janela do Nautilus (via o sinal
   `window-added` do Gtk.Application), o que intercepta o F4 antes de qualquer widget.

2) Abria na home, não na pasta: o ghostty é single-instance — quando já há janela aberta,
   uma nova invocação delega para o processo existente e IGNORA o `cwd=` do lançador. Por
   isso passamos o diretório explicitamente com `--working-directory=`. Para outros
   terminais caímos na função oficial (que usa cwd=), que basta.

A pasta é lida da aba ativa da janela onde o F4 foi apertado (`active-slot` → `location`);
`get_background_items` (chamado a cada navegação) só rastreia um fallback global. Instalado em ~/.local/share/ para sobreviver a updates do pacote oficial.
"""

import importlib.util
import sys
from os.path import expanduser
from subprocess import Popen
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GObject, Gtk  # noqa: E402

try:
    gi.require_version("Nautilus", "4.1")
except ValueError:
    gi.require_version("Nautilus", "4.0")
from gi.repository import Nautilus  # noqa: E402

_OAT_PATH = "/usr/share/nautilus-python/extensions/nautilus_open_any_terminal.py"
GSETTINGS_PATH = "com.github.stunkymonkey.nautilus-open-any-terminal"
GSETTINGS_BIND_REMOTE = "bind-remote"
GSETTINGS_TERMINAL = "terminal"
REMOTE_URI_SCHEME = ("ftp", "sftp")


def _load_oat():
    """Reaproveita o módulo oficial (já carregado ou importado) para usar as funções de
    abertura com os globais já inicializados — fallback para terminais que não o ghostty."""
    mod = sys.modules.get("nautilus_open_any_terminal")
    if mod is not None and hasattr(mod, "open_local_terminal_in_uri"):
        return mod
    try:
        spec = importlib.util.spec_from_file_location("_oat_f4_reuse", _OAT_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # roda o init do fim do módulo (set_terminal_args)
        return mod
    except Exception as exc:  # noqa: BLE001
        print(f"[open_terminal_f4] não consegui carregar o módulo oficial: {exc}")
        return None


_oat = _load_oat()


def _to_path(location: str) -> str:
    """previous_cwd vem como caminho puro (get_location().get_path()); normaliza file:// por segurança."""
    if location.startswith("file://"):
        return unquote(urlparse(location).path)
    return location


class OpenTerminalF4(GObject.GObject, Nautilus.MenuProvider):
    """Rastreia a pasta atual e instala o handler de F4 em cada janela do Nautilus."""

    def __init__(self):
        super().__init__()
        self.previous_cwd = expanduser("~")

        source = Gio.SettingsSchemaSource.get_default()
        self._gsettings = (
            Gio.Settings.new(GSETTINGS_PATH)
            if source is not None and source.lookup(GSETTINGS_PATH, True)
            else None
        )

        self._app = Gtk.Application.get_default()
        if self._app is None:
            print("[open_terminal_f4] nenhum Gtk.Application; F4 não será instalado.")
            return
        for window in self._app.get_windows():
            self._hook_window(window)
        self._app.connect("window-added", lambda _app, win: self._hook_window(win))

    # --- rastreio da pasta atual (chamado pelo Nautilus a cada navegação) ---
    def get_background_items(self, *args):
        folder = args[-1]
        if folder is not None:
            scheme = folder.get_uri_scheme()
            path = folder.get_uri() if scheme in REMOTE_URI_SCHEME else folder.get_location().get_path()
            if path:
                self.previous_cwd = path
        return []

    def get_file_items(self, *args):
        return []

    # --- instalação do handler de tecla ---
    def _hook_window(self, window):
        if getattr(window, "_f4_terminal_hooked", False):
            return
        window._f4_terminal_hooked = True
        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", self._on_key_pressed)
        window.add_controller(controller)

    def _on_key_pressed(self, controller, keyval, _keycode, _state):
        if keyval != Gdk.KEY_F4:
            return False
        self._open_terminal(self._window_location(controller.get_widget()))
        return True

    def _window_location(self, window):
        """Pasta da aba ativa DESTA janela (propriedades `active-slot` → `location` do
        Nautilus). `previous_cwd` é global — com várias janelas guarda a última navegada em
        qualquer uma delas, e trocar de janela/aba não o atualiza. Fica só como fallback."""
        try:
            location = window.get_property("active-slot").get_property("location")
        except (TypeError, AttributeError):
            location = None
        if location is None:
            return self.previous_cwd
        if location.get_uri_scheme() in REMOTE_URI_SCHEME:
            return location.get_uri()
        return location.get_path() or self.previous_cwd

    def _open_terminal(self, cwd):
        remote = self._gsettings is not None and self._gsettings.get_boolean(GSETTINGS_BIND_REMOTE)
        terminal = self._gsettings.get_string(GSETTINGS_TERMINAL) if self._gsettings else "ghostty"

        # ghostty é single-instance: precisa do diretório explícito, senão herda o da instância viva.
        if not remote and terminal == "ghostty":
            path = _to_path(cwd)
            Popen(["ghostty", f"--working-directory={path}"], cwd=path)  # noqa: S603
            return

        if _oat is None:
            print("[open_terminal_f4] módulo oficial indisponível; não é possível abrir o terminal.")
            return
        if remote:
            _oat.open_remote_terminal_in_uri(cwd)
        else:
            _oat.open_local_terminal_in_uri(cwd)
