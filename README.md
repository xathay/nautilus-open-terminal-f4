# nautilus-open-terminal-f4

Um atalho **F4** (tecla pura, sem modificador) para abrir o terminal **na pasta atual** do
GNOME Files (Nautilus 4.x / GTK4). Companheiro da extensão oficial
[`nautilus-open-any-terminal`](https://github.com/Stunkymonkey/nautilus-open-any-terminal),
reaproveitando a configuração dela (terminal escolhido, `bind-remote`, etc.).

## Por que existe

A extensão oficial já permite abrir um terminal na pasta atual, mas o **atalho de teclado**
não funciona para uma tecla pura como F4, e — com alguns terminais — abre na home em vez da
pasta certa. Esta extensão contorna dois problemas reais:

1. **F4 puro não dispara.** No Nautilus 4.x a única API de extensão disponível é
   `MenuProvider` (`LocationWidgetProvider` não existe na typelib `Nautilus-4.1`). A extensão
   oficial registra o atalho via `Gtk.Application.set_accels_for_action`, mecanismo que no
   GTK4 **não dispara com teclas sem modificador** — o `"F4"` é aceito, mas nunca acionado.
   Por isso o padrão dela é `<Ctrl><Alt>t`.
   → Aqui anexamos um `Gtk.EventControllerKey` na fase **CAPTURE** a cada janela do Nautilus
   (via o sinal `window-added` do `Gtk.Application`), interceptando o F4 antes de qualquer
   widget.

2. **Terminais single-instance abrem na home.** O
   [Ghostty](https://ghostty.org) (e outros terminais single-instance) delegam uma nova
   invocação ao processo já em execução e **ignoram o `cwd=`** do processo lançador,
   herdando o diretório da instância antiga. A extensão oficial só usa `Popen(cwd=...)`.
   → Aqui, para o Ghostty, passamos o diretório explicitamente com `--working-directory=`.
   Para os demais terminais caímos na função de abertura oficial.

A pasta atual é rastreada por `get_background_items`, que o Nautilus chama a cada navegação.

## Requisitos

- GNOME Files / Nautilus 4.x (GTK4)
- `nautilus-python`
- [`nautilus-open-any-terminal`](https://github.com/Stunkymonkey/nautilus-open-any-terminal)
  instalado e configurado (esta extensão reaproveita as funções e as `GSettings` dele)

## Instalação

```bash
./install.sh
```

O script cria um symlink de `open_terminal_f4.py` em
`~/.local/share/nautilus-python/extensions/`, limpa o `keybindings` das GSettings oficiais
(para não deixar um acelerador de aplicação "morto") e reinicia o Nautilus.

Depois: abra uma pasta e aperte **F4**.

## Desinstalação

```bash
./install.sh --uninstall
```

## Licença

GPL-3.0-or-later — reaproveita código da `nautilus-open-any-terminal`, também GPL.
