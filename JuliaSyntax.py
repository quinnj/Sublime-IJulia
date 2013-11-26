import sublime, sublime_plugin

class JuliaSyntaxCommand(sublime_plugin.WindowCommand):
    def run(self):
    	views = self.window.views()
    	for v in views:
    		if v.file_name() == None:
    			continue
    		elif v.file_name()[-2:] == 'jl':
    			v.set_syntax_file("Packages/IJulia/Syntax/Julia.tmLanguage")