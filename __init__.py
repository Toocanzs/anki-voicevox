from aqt import browser, gui_hooks, qt
from . import voicevox_gen

def on_browser_will_show_context_menu(browser: browser.Browser, menu: qt.QMenu):
    menu.addSeparator()
    menu.addAction("Generate VOICEVOX Audio", lambda: voicevox_gen.onVoicevoxOptionSelected(browser))
    
gui_hooks.browser_will_show_context_menu.append(on_browser_will_show_context_menu)