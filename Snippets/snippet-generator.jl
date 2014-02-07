cd("C:/Users/karbarcca/AppData/Roaming/Sublime Text 3/Packages/IJulia/Snippets")
include("C:/Users/karbarcca/julia/doc/helpdb.jl")
t = ans
f = open("julia.sublime-completions","w")
write(f,"{\n \"scope\": \"source.julia\",\n\n\"completions\":\n[")
for fun in t
	ismatch(r"[@|*|/|+|\$|\\|\-|&|%|\||<|>|^]",fun[3]) && continue
	write(f,"{ \"trigger\": \"")
	write(f,strip(fun[3]))
	write(f,"\", \"contents\": \"")
	sig = split(fun[4],'\r')[1]
	name = match(r"^.+(?=\()",sig)
	if typeof(name) == Nothing 
		write(f,sig)
		if fun != t[end]
			write(f,"\" },\n")
		else
			write(f,"\" }\n")
		end
		continue
	end
	name = name.match
	args = replace(sig,name,"")
	if args == "()"
		write(f,name)
		write(f,args)
		if fun != t[end]
			write(f,"\" },\n")
		else
			write(f,"\" }\n")
		end
		continue
	end
	args = args[2:end-1]
	write(f,name)
	write(f,"(")
	args = split(args,',')
	for i = 1:length(args)
		args[i] = replace(args[i],'\"',"\\\"")
		write(f,"\${$i:$(args[i])}")
		i != length(args) && write(f,',')
	end
	write(f,")")	
	if fun != t[end]
		write(f,"\" },\n")
	else
		write(f,"\" }\n")
	end
end
write(f,"]\n}")
close(f)