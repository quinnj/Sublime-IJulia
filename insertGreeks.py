import sublime, sublime_plugin
greeks = { 
'a':'α',
'b':'β',
'g':'γ',
'd':'δ',
'ep':'ε',
'z':'ζ',
'et':'η',
'th':'θ',
'i':'ι',
'k':'κ',
'l':'λ',
'm':'μ',
'n':'ν',
'x':'ξ',
'omi':'ο',
'pi':'π',
'r':'ρ',
's':'σ',
't':'τ',
'u':'υ',
'phi':'φ',
'c':'χ',
'psi':'ψ',
'ome':'ω',
'A':'Α',
'B':'Β',
'G':'Γ',
'D':'Δ',
'Ep':'Ε',
'Z':'Ζ',
'Et':'Η',
'Th':'Θ',
'I':'Ι',
'K':'Κ',
'L':'Λ',
'M':'Μ',
'N':'Ν',
'X':'Ξ',
'Omi':'Ο',
'Pi':'Π',
'R':'Ρ',
'S':'Σ',
'T':'Τ',
'U':'Υ',
'Phi':'Φ',
'C':'Χ',
'Psi':'Ψ',
'Ome':'Ω'
}

class InsertGreekCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		currsel = self.view.sel()[0]
		currword = self.view.word(currsel)
		k = self.view.substr(currword)
		if (k in greeks):
			self.view.replace(edit, currword, greeks[k])