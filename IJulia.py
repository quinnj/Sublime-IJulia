import os, sublime, sublime_plugin
from . import KernelManager

SETTINGS_FILE = 'Sublime-IJulia.sublime-settings'

class IJuliaManager(object):
    def __init__(self):
        self.julia_views = []
        self.text_transfer = ""
        self.cmdhist = [""]

    #where can this be called from?
    def julia_view(self, view):
        julia_id = view.settings().get("julia_id")
        try:        
            jv = self.julia_views[julia_id]
        except:
            return None
        jv.update_view(view) #what does this do
        return jv

    def open(self, window):
        id = len(self.julia_views)
        view = window.new_file()
        jv = IJuliaView(view, id)
        self.julia_views.append(jv)
        view.set_scratch(True)
        view.set_name("*IJulia %d*" % id)
        return jv        

    def restart(self, jv, edit):
        jv.on_close()
        id = len(self.julia_views)
        jv = IJuliaView(jv._view, id)
        self.julia_views.append(jv)
        view.set_scratch(True)
        view.set_name("*IJulia %d*" % id)
        return True

    def remove_ijulia_view(self, julia_view):
        julia_id = julia_view.id
        try:
            del self.julia_views[julia_id]
        except:
            return None
        for i in range(0,len(self.julia_views)):
            self.julia_views[i]._view.settings().set("julia_id", i)
            self.julia_views[i]._view.set_name("IJulia %d*" % i)

manager = IJuliaManager()

class IJuliaView(object):
    def start_kernel(self):
        print("starting kernel...")
        self.kernel = KernelManager.KernelManager(self.cmd, self.id, self.profile)
        self.reader = KernelManager.RecvThread(self.kernel, self)
        self.reader.start()
        self.kernel.execute("Base.banner()")

    def __init__(self, view, id):
        self.id = id
        settings = sublime.load_settings(SETTINGS_FILE)
        cmd = settings.get("julia_command")
        if sublime.platform() == 'windows':
            cmd = cmd["windows"]
        else:
            cmd = cmd["unix"]
        filename = "\"" + sublime.packages_path() + '/User/profile-' + str(id) + '.json\"'
        self.cmd = cmd + " " + os.path.expanduser("~/.julia/IJulia/src/kernel.jl ") + filename
        self.profile = KernelManager.zmq_profile(filename, id)
        sublime.set_timeout_async(self.start_kernel,0)
        self._view = view
        self._output_end = view.size()
        self._window = view.window()
        self.cmdstate = -1
        self.in_count = 1
        self.stdout_pos = 0
        view.settings().set("julia",True)
        view.set_syntax_file("Packages/IJulia/Syntax/Julia.tmLanguage")
        view.settings().set("julia_id", id)
        (group, index) = self._window.get_view_index(view)
        oldview = self._window.views_in_group(group)[max(0, index-1)]
        self._window.set_view_index(view, group + 1, len(self._window.views_in_group(group + 1)))
        self._window.focus_view(oldview)
        self._window.focus_view(view)

    def shift_enter(self, edit):
        self._view.run_command("i_julia_insert_text", 
            {"pos": self._view.size(), "text": '\n\t\t '})

    def on_backspace(self):
        if self.delta < 0:
            self._view.run_command("left_delete")

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
        self.kernel.kernel.poll()
        if self.kernel.kernel.returncode == None:
            self.kernel.shutdown(False)
        manager.remove_ijulia_view(self)

    def kernel_died(self):
        self.write("\n\n***Kernel Died***\n",True)
        self._view.set_read_only(True)
        manager.remove_ijulia_view(self)        

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
        self.write(text,False)
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
        self.write(text,False)
        self._view.show(self.input_region)

    def write(self, unistr, extend):
        self._view.run_command("i_julia_insert_text", {"pos": self._output_end, "text": unistr})
        if extend:
            self._output_end += len(unistr) 

    def enter(self, edit):
        v = self._view
        if v.sel()[0].begin() != v.size():
            v.sel().clear()
            v.sel().add(sublime.Region(v.size()))
        command = self.user_input
        v.run_command("insert", {"characters": '\n'})
        self._output_end += len(command)
        self.stdout_pos = self._output_end
        manager.cmdhist.insert(0,command)
        manager.cmdhist = list(self.unique(manager.cmdhist))
        self.cmdstate = -1
        self.command = command
        sublime.set_timeout_async(self.execute,0)
        
    def execute(self):
        self.kernel.execute(self.command)

    def stdout_output(self, data):
        data = data.replace('\r\n','\n')
        self._view.run_command("i_julia_insert_text", 
            {"pos": self.stdout_pos, "text": data})
        self._output_end += len(data)
        self.stdout_pos = self._output_end

    def in_output(self):
        self.write("\nIn  [{:d}]: ".format(self.in_count),True)
        self.in_count += 1
        self.reader.startup = 0

    def output(self, count, data):
        out = "\nOut [{:d}]: {!s}\n".format(self.in_count-1, data)
        self.write(out,True)
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

# Window Commands #########################################
# Opens a new REPL
class IJuliaOpenCommand(sublime_plugin.WindowCommand):
    def run(self):
        manager.open(self.window)

class IJuliaRestartCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            manager.restart(rv, edit)

    def is_enabled(self):
        return self.is_visible()

class IJuliaTransferCurrent(sublime_plugin.TextCommand):
    def run(self, edit, scope="selection"):
        text = ""
        if scope == "selection":
            text = self.selected_text()
        elif scope == "lines":
            text = self.selected_lines()
        elif scope == "file":
            text = self.selected_file()
        
        mg = manager
        jvs = mg.julia_views
        if len(jvs) == 0:
            jv = mg.open(self.view.window())
            #need to wait to write text until after banner is displayed
            jv.write(text,False)
            jv.enter(edit)
        elif len(jvs) > 1:
            mg.text_transfer = text
            panel_list = []
            for v in jvs:
                panel_list.append(v._view.name())
            self.view.window().show_quick_panel(panel_list, self.choose_julia,sublime.MONOSPACE_FONT)
        else:
            jv = jvs[0]
            jv.write(text,False)
            jv.enter(edit)

    def choose_julia(edi,num):
            if num == -1:
                return
            jv = manager.julia_views[num]
            jv.write(manager.text_transfer,False)
            jv._view.run_command("i_julia_enter", {})

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


# IJulia Comands ############################################
class IJuliaInsertTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, pos, text):
        self.view.set_read_only(False)
        self.view.insert(edit, int(pos), text)

class IJuliaEraseTextCommand(sublime_plugin.TextCommand):
    def run(self, edit, start, end):
        self.view.set_read_only(False)
        self.view.erase(edit, sublime.Region(int(start), int(end)))

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

class IJuliaEscapeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.escape(edit)

class IJuliaBackspaceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_backspace()

class IJuliaLeftCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_left()

class IJuliaShiftLeftCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_shift_left()


class IJuliaHomeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_home()

class IJuliaShiftHomeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.on_shift_home()

class IJuliaViewPreviousCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.previous_command(edit)

class IJuliaViewNextCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.next_command(edit)

class JuliaPass(sublime_plugin.TextCommand):
    def run(self, edit):
        pass

class IJuliaListener(sublime_plugin.EventListener):
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

        if command_name == 'left_delete':
            # stop backspace on ST3 w/o breaking brackets
            if not rv.allow_deletion():
                return 'julia_pass', {}

        if command_name == 'delete_word' and not args.get('forward'):
            # stop ctrl+backspace on ST3 w/o breaking brackets
            if not rv.allow_deletion():
                return 'julia_pass', {}

        return None