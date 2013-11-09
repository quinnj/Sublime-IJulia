import os, sublime, sublime_plugin
from . import KernelManager
from .ZMQ import pkg_dir

SETTINGS_FILE = 'Sublime-IJulia.sublime-settings'

class JuliaView(object):
    def start_kernel(self):
        print("starting kernel...")
        self.kernel = KernelManager.KernelManager(self.cmd, self.id)
        self.reader = KernelManager.RecvThread(self.kernel, self)
        self.reader.start()
        self.kernel.execute("Base.banner()")

    def __init__(self, view, id):
        self.id = id
        settings = sublime.load_settings(SETTINGS_FILE)
        cmd = settings.get("julia_command")
        if os.name == 'nt':
            cmd = cmd["windows"]
        else:
            cmd = cmd["unix"]
        self.cmd = cmd + " " + pkg_dir + "/IJulia/src/kernel.jl "
        sublime.set_timeout_async(self.start_kernel,0)        
        self._view = view
        self._output_end = view.size()
        self._window = view.window()
        self.cmdstate = -1
        self.banner = 1
        self.in_count = 1
        view.settings().set("julia",True)
        view.set_syntax_file("Packages/IJulia/Syntax/Julia.tmLanguage")
        view.settings().set("julia_id", id)
        (group, index) = self._window.get_view_index(view)
        oldview = self._window.views_in_group(group)[max(0, index-1)]
        self._window.set_view_index(view, group + 1, len(self._window.views_in_group(group + 1)))
        self._window.focus_view(oldview)
        self._window.focus_view(view)

    def shift_enter(self, edit):
        self._view.run_command("julia_insert_text", {"pos": self._view.size(), "text": '\n\t\t '})

    def on_backspace(self):
        if self.delta < 0:
            self._view.run_command("left_delete")

    def on_ctrl_backspace(self):
        if self.delta < 0:
            self._view.run_command("delete_word", {"forward": False, "sub_words": True})

    def on_super_backspace(self):
        if self.delta < 0:
            for i in range(abs(self.delta)):
                self._view.run_command("left_delete")  # Hack to delete to BOL

    def on_left(self):
        if self.delta != 0:
            self._window.run_command("move", {"by": "characters", "forward": False, "extend": False})

    def on_shift_left(self):
        if self.delta != 0:
            self._window.run_command("move", {"by": "characters", "forward": False, "extend": True})

    def on_home(self):
        if self.delta > 0:
            self._window.run_command("move_to", {"to": "bol", "extend": False})
        else:
            for i in range(abs(self.delta)):
                self._window.run_command("move", {"by": "characters", "forward": False, "extend": False})

    def on_shift_home(self):
        if self.delta > 0:
            self._window.run_command("move_to", {"to": "bol", "extend": True})
        else:
            for i in range(abs(self.delta)):
                self._window.run_command("move", {"by": "characters", "forward": False, "extend": True})

    def on_selection_modified(self):
        self._view.set_read_only(self.delta > 0)

    def on_close(self):
        self.kernel.shutdown(False)
        manager._delete_repl(self)

    def clear(self, edit):
        self.escape(edit)
        self._view.erase(edit, self.output_region)
        self._output_end = self._view.sel()[0].begin()

    def escape(self, edit):
        self._view.set_read_only(False)
        self._view.erase(edit, self.input_region)
        self._view.show(self.input_region)
        self.cmdstate = -1

    def unique(self, seq):
        seen = set()
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            yield x

    def previous_command(self, edit):
        self._view.set_read_only(False)
        self._view.erase(edit,self.input_region)
        self._view.show(self.input_region)
        if self.cmdstate < len(manager.cmdhist)-1:
            self.cmdstate += 1
        text = manager.cmdhist[self.cmdstate]
        self._view.run_command("julia_insert_text", {"pos": self._output_end, "text": text})
        self._view.show(self.input_region)

    def next_command(self, edit):
        self._view.set_read_only(False)
        self._view.erase(edit,self.input_region)
        self._view.show(self.input_region)
        if self.cmdstate == -1:
            return
        elif self.cmdstate == 0:
            text = ''
        else:
            text = manager.cmdhist[self.cmdstate-1]
        self.cmdstate -= 1
        self._view.run_command("julia_insert_text", {"pos": self._output_end, "text": text})
        self._view.show(self.input_region)

    def write(self, unistr):
        self._view.run_command("julia_insert_text", {"pos": self._output_end, "text": unistr})
        self._output_end += len(unistr) 

    def enter(self, edit):
        v = self._view
        if v.sel()[0].begin() != v.size():
            v.sel().clear()
            v.sel().add(sublime.Region(v.size()))
        v.run_command("insert", {"characters": '\n'})
        command = self.user_input
        self._output_end += len(command)
        manager.cmdhist.insert(0,command[:-1])
        manager.cmdhist = list(self.unique(manager.cmdhist))
        self.cmdstate = -1
        self.command = command
        sublime.set_timeout_async(self.execute,0)
        
    def execute(self):
        self.kernel.execute(self.command)

    def stdout_output(self, data):
        if data != '\n':
            self.write(data.replace('\r\n','\n'))
            self._output_end = self._view.size()

    def in_output(self):
        self.write("\nIn  [{:d}]: ".format(self.in_count))
        self.reader.startup = 0
        self.in_count += 1

    def output(self, count, data):
        self.write("\nOut [{:d}]: {!s}".format(self.in_count-1, data))
        self._view.run_command("insert", {"characters": '\n'})
        self._output_end = self._view.size()

    @property
    def input_region(self):
        return sublime.Region(self._output_end, self._view.size())

    @property
    def output_region(self):
        return sublime.Region(0, self._output_end)

    @property
    def user_input(self):
        return self._view.substr(self.input_region)

    @property
    def delta(self):
        return self._output_end - self._view.sel()[0].begin()

    def update_view(self, view):
        if self._view is not view:
            self._view = view

    def allow_deletion(self):
        _output_end = self._output_end
        for sel in self._view.sel():
            if sel.begin() == sel.end() and sel.begin() == _output_end:
                return False
            if sel.begin() < _output_end or sel.end() < _output_end:
                return False
        return True


class IJuliaManager(object):
    def __init__(self):
        self.julia_views = {}
        self.text_transfer = ""
        self.cmdhist = ['']

    def julia_view(self, view):
        julia_id = view.settings().get("julia_id")
        if julia_id not in self.julia_views:
            return None
        jv = self.julia_views[julia_id]
        jv.update_view(view)
        return jv

    def open(self, window):
        id = len(self.julia_views)
        found = None
        for view in window.views():
            if view.settings().get("julia_id") == id:
                found = view
                break
        view = found or window.new_file()
        jv = JuliaView(view, id)
        self.julia_views[id] = jv
        view.set_scratch(True)
        view.set_name("*IJulia %d*" % id)
        return jv        

    def restart(self, view, edit):
        # need to shift other views down in id
        jv = self.julia_view(view)
        if jv:
            jv.on_close()
        view.run_command("insert", {"characters": '                         '})
        self.open(view.window())
        for i in range(0,25):
           view.run_command("left_delete")
        return True

    def _delete_repl(self, julia_view):
        julia_id = julia_view.juliarepl.id
        if julia_id not in self.julia_views:
            return None
        del self.julia_views[julia_id]


manager = IJuliaManager()

# Window Commands #########################################
# Opens a new REPL
class IJuliaOpenCommand(sublime_plugin.WindowCommand):
    def run(self):
        manager.open(self.window)

class JuliaRestartCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        manager.restart(self.view, edit)

    def is_enabled(self):
        return self.is_visible()

class JuliaTransferCurrent(sublime_plugin.TextCommand):
    def run(self, edit, scope="selection"):
        text = ""
        if scope == "selection":
            text = self.selected_text()
        elif scope == "lines":
            text = self.selected_lines()
        elif scope == "file":
            text = self.selected_file()
        
        mg = manager
        mg.text_transfer = text
        mg.edit_chunk = edit
        jvs = mg.julia_views
        if len(jvs) == 0:
            jv = mg.open(self.view.window())
            jv._view.run_command("julia_insert_text", {"pos": jv._output_end, "text": text})
            jv.enter(edit)
        elif len(jvs) > 1:
            panel_list = []
            for v in jvs:
                panel_list.append(jvs[v]._view.name())
            self.view.window().show_quick_panel(panel_list, self.choose_julia,sublime.MONOSPACE_FONT)
        else:
            jv = jvs[0]
            jv._view.run_command("julia_insert_text", {"pos": jv._output_end, "text": text})
            jv.enter(edit)

    def choose_julia(edi,num):
            if num == -1:
                return
            jv = manager.julia_views[num]
            jv._view.run_command("julia_insert_text", {"pos": jv._output_end, "text": manager.text_transfer})
            jv._view.run_command("julia_enter", {})

    def selected_text(self):
        v = self.view
        parts = [v.substr(region) for region in v.sel()]
        return "".join(parts)

    def selected_lines(self):
        v = self.view
        parts = []
        for sel in v.sel():
            for line in v.lines(sel):
                parts.append(v.substr(line))
        return "\n".join(parts)

    def selected_file(self):
        v = self.view
        return v.substr(sublime.Region(0, v.size()))


# REPL Comands ############################################
class JuliaInsertTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, pos, text):
        self.view.set_read_only(False)  # make sure view is writable
        self.view.insert(edit, int(pos), text)


class JuliaEraseTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, start, end):
        self.view.set_read_only(False)  # make sure view is writable
        self.view.erase(edit, sublime.Region(int(start), int(end)))


class JuliaPass(sublime_plugin.TextCommand):
    def run(self, edit):
        pass

# Submits the Command to the REPL
class IJuliaEnterCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.enter(edit)

class IJuliaShiftEnterCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.shift_enter(edit)

class JuliaClearCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.clear(edit)

# Resets Julia Command Line
class JuliaEscapeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.escape(edit)


class JuliaBackspaceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_backspace()


class JuliaCtrlBackspaceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_ctrl_backspace()


class JuliaSuperBackspaceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_super_backspace()


class JuliaLeftCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_left()


class JuliaShiftLeftCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_shift_left()


class JuliaHomeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_home()


class JuliaShiftHomeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_shift_home()


class JuliaViewPreviousCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.previous_command(edit)


class JuliaViewNextCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.next_command(edit)


class JuliaKillCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.juliarepl.kill()

    def is_visible(self):
        rv = manager.julia_view(self.view)
        return bool(rv)

    def is_enabled(self):
        return self.is_visible()


class SublimeReplListener(sublime_plugin.EventListener):
    def on_selection_modified(self, view):
        rv = manager.julia_view(view)
        if rv:
            rv.on_selection_modified()

    def on_close(self, view):
        rv = manager.julia_view(view)
        if rv:
            rv.on_close()

    def on_text_command(self, view, command_name, args):
        rv = manager.julia_view(view)
        if not rv:
            return None

        if command_name == 'insert':
            # with "auto_complete_commit_on_tab": true enter does
            # not work when autocomplete is displayed, this fixes
            # it by replacing insert \n with repl_enter
            if args.get('characters') == '\n':
                view.run_command('hide_auto_complete')
                return 'julia_enter', {}
            return None

        if command_name == 'left_delete':
            # stop backspace on ST3 w/o breaking brackets
            if not rv.allow_deletion():
                return 'julia_pass', {}

        if command_name == 'delete_word' and not args.get('forward'):
            # stop ctrl+backspace on ST3 w/o breaking brackets
            if not rv.allow_deletion():
                return 'julia_pass', {}

        return None

class SubprocessReplSendSignal(sublime_plugin.TextCommand):
    def run(self, edit, signal=None):
        rv = manager.julia_view(self.view)
        subrepl = rv.juliarepl
        signals = subrepl.available_signals()
        sorted_names = sorted(signals.keys())
        if signal in signals:
            #signal given by name
            self.safe_send_signal(subrepl, signals[signal])
            return
        if signal in list(signals.values()):
            #signal given by code (correct one!)
            self.safe_send_signal(subrepl, signal)
            return

        # no or incorrect signal given
        def signal_selected(num):
            if num == -1:
                return
            signame = sorted_names[num]
            sigcode = signals[signame]
            self.safe_send_signal(subrepl, sigcode)
        self.view.window().show_quick_panel(sorted_names, signal_selected)

    def safe_send_signal(self, subrepl, sigcode):
        try:
            subrepl.send_signal(sigcode)
        except Exception as e:
            sublime.error_message(str(e))

    def is_visible(self):
        rv = manager.julia_view(self.view)
        return bool(rv) and hasattr(rv.juliarepl, "send_signal")

    def is_enabled(self):
        return self.is_visible()

    def description(self):
        return "Send SIGNAL"
