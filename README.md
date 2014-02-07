Sublime-IJulia
======

Successor to the Sublime-Julia project, now based on the IJulia backend.

Julia is a new, open-source technical computing language built for speed and simplicity. The IJulia project
built an IPython kernel for Julia to provide the typical IPython frontend-backend functionality such as
the popular notebook, qtconsole, and regular terminal. 

Sublime-IJulia builds on these efforts by providing a frontend to the IJulia backend kernel within the popular text editor, Sublime Text. All within Sublime, 
a user can start up an IJulia frontend in a Sublime view and interact with the kernel. This allows for rapid 
code development through REPL testing and debugging without ever having to leave our favorite editor.

This project is still in beta, so please be patient and open [issues](https://github.com/karbarcca/Sublime-IJulia/issues) liberally.

#### ZMQ/IJulia Installation
Before installing the Sublime-IJulia package, you must first ensure you have added and successfully built the `ZMQ` julia package from within julia itself. You will also need the `IJulia` to be added, though not necessarily successfully built (the reason is that `IJulia` requires IPython to be installed, while Sublime-IJulia does *not* require IPython). Simply adding the IJulia package will ensure the needed files are installed, whether or not it can be used with ipython (though the use of IPython notebooks is highly encouraged for code presentation!) These steps can be done by running the following from within julia:
```julia
Pkg.add("ZMQ")    # Needs to install and build successfully
Pkg.add("IJulia") # Needs to install, but not necessarily build successfully
```
See the [IJulia](https://github.com/JuliaLang/IJulia.jl) page for additional help.


#### Sublime-IJulia Installation
The Sublime-IJulia project requires Sublime Text 3 with build version > 3019. You can get the latest version [here](http://www.sublimetext.com/3).


1. Within Sublime Text 3, install the Package Control package from [here](https://sublime.wbond.net/installation)
2. With Package Control successfully installed, run `Ctrl+Shift+p` (`Cmd+Shift+p` on OSX) to open the Sublime command pallette and start typing "Install Package", then select "Package Control: Install Package".
3. From the list of packages that are then shown, start typing "IJulia" and then select the "IJulia" package. This installs the IJulia package into your Sublime packages directory.
4. From the menu bar, open `Preferences => Package Settings => Sublime-IJulia => Settings - Default`
5. Then, from the menu bar, open `Preferences => Package Settings => Sublime-IJulia => Settings - User`
6. Copy everything from the `Settings - Default` file into the `Settings - User` file
7. Now, in the `Settings - User` file, scroll down to your platform and on Windows and for the most part Linux, you should *not* have to change the `zmq_shared_library` field value. These are the expected standard installation locations when installing/building the ZMQ package from within julia, so they should work out of the box. For OSX, the default value is a best guess, but the value is subject to change depending on where homebrew ends up installing the ZMQ library when building the ZMQ or IJulia package from within julia. Also note for Linux that if the ZMQ library was already installed via apt/yum, the default path will not be correct. The easiest way to locate your ZMQ library (on any platform) is to to run the following commands from within julia: `using ZMQ; ZMQ.zmq`. Sometimes, all that is returned is `libzmq` which obviously isn't that helpful. In any case, if you do a file system search for `libzmq`, you should be able to locate the absolute path to the library which is needed for your `zmq_shared_library` settings value. *PLEASE NOTE: When setting your path, you MUST specify the library extension as well. `/path/to/zmq/libzmq.so` or `/path/to/zmq/libzmq.so.3` for linux, `/path/to/zmq/libzmq.dylib` for OSX, and `/path/to/zmq/libzmq.dll` on windows.* This is by far the toughest step to manage because of the cross-platform issues and non-standard installation locations, but be willing to try a few different paths and restart Sublime in between each attempt. If you're still having issues, please open an issue as mentioned above.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             8. Now change the value of the `"julia": "julia",` field to the absolute path to your julia executable. If julia is on your path, this may not involve changing anything (i.e if you can type `julia` or `julia-readline` from the command line from any directory). Otherwise put the full path to your julia executable (i.e. `/usr/home/julia/usr/bin/julia`).
9. With the above two values properly set in the settings file (you should *not* have to change the "ijulia_kernel" value, you can now run `Ctrl+Shift+p` to open the command pallette and start typing "Open IJulia" and select "Sublime-IJulia: Open New IJulia Console". If all goes well, a new view should open up in Sublime, titled `*IJulia 0*` and the julia banner should display shortly (2-5 seconds). Success!
10. If an error message pops up, it's probably because Sublime can't find your ZMQ library or julia executable, return to step 7/8. If `***Kernel Died***` shows up in a new view, there's been some kind of error in your julia command, so return to step 7. In any case, please go back over the steps to ensure everything was followed, restart Sublime, and if the results are the same, please open an issue [here](https://github.com/karbarcca/Sublime-IJulia/issues) and I'm more than happy to help troubleshoot the installation.

#### Using Sublime-IJulia
* Commands can be entered directly in the IJulia console view, pressing `enter` to execute. 
* A newline can be entered without executing the command by typing `Shift+Enter` for multi-line commands.
* Pressing the `up` and `down` arrows in the console view will navigate through command history (if any).
* `escape` will clear the current command
* All other regular sublime features should work as normal also in the console view (multiple cursors, macros, etc.)


From a julia file (extension .jl), you also have the ability to "send" code to the console to be evaluated. 
* `Ctrl+enter` without any code selected will send the current line to the console to be executed
* `Ctrl+enter` with code selected will send the selected text to the console to be executed
* `Ctrl+shift+enter` will send the entire file's contents to the console to be executed

#### Other Sublime-IJulia Package Features
* Auto-completion: Most of the [stdlib](http://docs.julialang.org/en/latest/stdlib/base/#) julia functions can be auto-completed from the console and julia (.jl) files. Just start typing a function name and press `tab` to auto-complete with the expected arguments.
* Syntax: Syntax highlighting is available for julia files (.jl), you can set them manually by clicking in the lower right-hand side of sublime (there will be "Text" or some other language displayed) and select "Julia" from the list
* You can also automatically apply the Julia syntax by typing `Ctrl+Shift+p` and start typing "Apply Julia syntax" and select that command. This will automatically apply the Julia syntax to all open (.jl) files.
* Build: A basic build file is provided, but will probably have to be manually tweaked to provide the path to your julia executable. This can be done by opening your Sublime packages folder, going to the IJulia directory and opening the `julia-build.sublime-build` file. Then you just have to change the "julia" in `"cmd": ["julia", "$file"],` to the same value you set in your settings file for `julia_command` (i.e. absolute path to julia, julia-readline, etc.). 
* Multiple julia commands can be set in the settings file. This is done by adding another "command" object to the "commands" array of your platform. If you were on windows, your entire platform key-value would be:

```json
"windows": {
    "zmq_shared_library": "~/.julia/v0.3/ZMQ/deps/usr/lib/libzmq.dll",
    "commands": [
        {
            "command_name": "default",
            "julia": "julia-readline.exe",
            "julia_args": "",
            "ijulia_kernel": "~/.julia/v0.3/IJulia/src/kernel.jl"
        },
        {
            "command_name": "timefork",
            "julia": "C:/Users/karbarcca/timefork/usr/bin/julia-readline.exe",
            "julia_args": "-p 4",
            "ijulia_kernel": "~/.julia/v0.3/IJulia/src/kernel.jl"
        }
    ]
}
```
Note the comma `,` after the original default command. Another command is then copied down. The `"julia":` field is changed to a separate julia executable (in this case, a separate branch of julia, but it could also be a past version of julia or whatever). There are also some arguments passed to the julia executable by `"julia_args": "-p 4"`, meaning to start the julia executable with 4 additional processors. With the above commands set, when I go to open a console with `ctrl+shift+p`, type "Open IJulia", a second popup will show me a list of

```
default
timefork
```
from which I can choose which julia I want to launch. 

Cheers!

-Jacob Quinn
