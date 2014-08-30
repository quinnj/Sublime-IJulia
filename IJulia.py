import os, time, sublime, sublime_plugin
from . import Kernel

SETTINGS_FILE = 'Sublime-IJulia.sublime-settings'

class IJuliaManager(object):
    def __init__(self):
        self.julia_views = []
        self.text_transfer = ""
        self.cmdhist = [""]

    def open(self, window, cmd):
        id = len(self.julia_views)
        view = window.new_file()
        jv = IJuliaView(view, id, cmd)
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

    def julia_view(self, view):
        julia_id = view.settings().get("julia_id")
        if julia_id == None:
            return None
        jv = self.julia_views[julia_id]
        #jv.update_view(view)
        return jv

    def remove_ijulia_view(self, view):
        julia_id = view._view.settings().get("julia_id")
        if julia_id == None:
            return None
        jvs = manager.julia_views
        del jvs[julia_id]
        for i in range(0,len(jvs)):
            jvs[i]._view.settings().set("julia_id", i)
            jvs[i]._view.set_name("IJulia %d*" % i)

manager = IJuliaManager()

class IJuliaView(object):
    def start_kernel(self):
        print("Starting IJulia backend...")
        self.kernel = Kernel.Kernel(self.id,self.cmd,self)
        self.kernel.start()
        self.kernel.queue.put_nowait("Base.banner()")

    def __init__(self, view, id, cmd):
        self.id = id
        self.cmd = cmd
        sublime.set_timeout_async(self.start_kernel,0)
        self._view = view
        self._output_end = view.size()
        self._window = view.window()
        self.cmdstate = -1
        self.in_count = 2
        self.stdout_pos = 0
        view.settings().set("julia",True)
        view.set_syntax_file("Packages/IJulia/Syntax/Julia.tmLanguage")
        view.settings().set("julia_id", id)
        (group, index) = self._window.get_view_index(view)
        oldview = self._window.views_in_group(group)[max(0, index-1)]
        self._window.set_view_index(view, group + 1, len(self._window.views_in_group(group + 1)))
        self._window.focus_view(oldview)
        self._window.focus_view(view)

    def on_close(self):
        self.kernel.kernel.poll()
        if self.kernel.kernel.returncode == None:
            self.kernel.shutdown(False)
        self.write("\n\n***Kernel Died***\n",True)
        self._view.set_read_only(True)
        manager.remove_ijulia_view(self)

    def interrupt(self):
        self.kernel.interrupt()

    def update_view(self, view):
        if self._view is not view:
            self._view = view

    def shift_enter(self, edit):
        if self.delta < 0:
            self._view.run_command("i_julia_insert_text", 
                {"pos": self._view.size(), "text": '\n'})

    def on_backspace(self):
        if self.delta < 0:
            if self._view.command_history(0)[0] == 'insert_snippet':
                self._view.run_command("run_macro_file",{"file": "res://Packages/Default/Delete Left Right.sublime-macro"})
            else:
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

    # def on_selection_modified(self):
    #     self._view.show_at_center(self._view.size()-75)

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

    def debug(self,func):
        print("%s: _output_end: %s" % (func,self._output_end))

    def enter(self, edit):
        v = self._view
        if v.sel()[0].begin() != v.size():
            v.sel().clear()
            v.sel().add(sublime.Region(v.size()))
        v.run_command("i_julia_insert_text", {"pos": v.sel()[0].begin(), "text": '\n'})
        command = self.user_input
        self._output_end += len(command)
        self.stdout_pos = self._output_end
        manager.cmdhist.insert(0,command[:-1])
        manager.cmdhist = list(self.unique(manager.cmdhist))
        self.cmdstate = -1
        self.kernel.queue.put_nowait(command)
        
    def stdout_output(self, data):
        data = data.replace('\r\n','\n')
        self._view.run_command("i_julia_insert_text", 
            {"pos": self.stdout_pos, "text": data})
        self._output_end += len(data)
        self.stdout_pos = self._output_end

    def in_output(self):
        self.write("\nIn  [{:d}]: ".format(self.in_count),True)
        self.in_count += 1
        self.kernel.startup = 0
        vec = self._view.text_to_layout(self._view.size())[1] - self._view.viewport_extent()[1] + 50.0
        self._view.set_viewport_position((0.0, max(0,vec)))

    def output(self, count, data):
        out = "\nOut [{:d}]: {!s}\n".format(self.in_count-1, data)
        self.write(out,True)

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

    def allow_deletion(self):
        o = self._output_end
        for sel in self._view.sel():
            if sel.begin() == sel.end() and sel.begin() == o:
                return False
            if sel.begin() < o or sel.end() < o:
                return False
        return True

# Window Commands #########################################
# Opens a new REPL
class IJuliaOpenCommand(sublime_plugin.TextCommand):
    def run(self,edit):
        settings = sublime.load_settings(SETTINGS_FILE)
        self.cmd = settings.get(sublime.platform())['commands']
        if len(self.cmd) == 1:
            manager.open(self.view.window(),self.cmd[0])
        else:
            panel_list = []
            for i in self.cmd:
                panel_list.append(i['command_name'])
            self.view.window().show_quick_panel(panel_list, self.run_custom,sublime.MONOSPACE_FONT)

    def run_custom(self,num):
        if num == -1:
            return
        manager.open(self.view.window(),self.cmd[num])

class IJuliaRestartCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            manager.restart(rv, edit)

    def is_enabled(self):
        return self.is_visible()

class IJuliaSetWorkingFolderToView(sublime_plugin.TextCommand):
    def run(self, edit):
        
        if not self.view.file_name():
            return
        
        import os
        fileDir = os.path.dirname( self.view.file_name() )
        
        cmd = 'cd("' + fileDir.replace("\\","\\\\") + '")'
        
        mg = manager
        jvs = mg.julia_views
        
        if (len(jvs) == 0):  # no julia views
            return
        elif len(jvs) > 1:
            mg.text_transfer = cmd
            panel_list = []
            for v in jvs:
                panel_list.append(v._view.name())
            self.view.window().show_quick_panel(panel_list, self.choose_julia,sublime.MONOSPACE_FONT)
        else:
            jv = jvs[0]
            jv.write(cmd,False)
            jv.enter(edit)
        
        
    def choose_julia(edi,num):
        if num == -1:
            return
        jv = manager.julia_views[num]
        jv.write(manager.text_transfer,False)
        jv._view.run_command("i_julia_enter", {})
            

class IJuliaTransferCurrent(sublime_plugin.TextCommand):
    def run(self, edit, scope="selection"):
        text = ""
        if scope == "selection":
            text = self.selected_text()
        elif scope == "lines":
            text = self.selected_lines()
        elif scope == "file":
            text = self.selected_file()
        elif scope == "file_with_include":
            # if view doesn't have a file name,
            #  it will ask for one
            self.view.run_command("save")
            text = 'include("' + self.view.file_name().replace("\\","\\\\") + '")'
        
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

class IJuliaInterrupt(sublime_plugin.TextCommand):
    def run(self, edit):
        rv = manager.julia_view(self.view)
        if rv:
            rv.interrupt()

class IJuliaListener(sublime_plugin.EventListener):
    #def on_selection_modified(self, view):
        #rv = manager.julia_view(view)
        # if rv:
        #     rv.on_selection_modified()

    def on_close(self, view):
        jv = manager.julia_view(view)
        if jv != None:
            jv.on_close()

    def on_text_command(self, view, command_name, args):
        rv = manager.julia_view(view)
        if not rv:
            return None

        # if command_name == 'left_delete':
        #     # stop backspace on ST3 w/o breaking brackets
        #     if not rv.allow_deletion():
        #         return 'julia_pass', {}

        # if command_name == 'delete_word' and not args.get('forward'):
        #     # stop ctrl+backspace on ST3 w/o breaking brackets
        #     if not rv.allow_deletion():
        #         return 'julia_pass', {}

        return None