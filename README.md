# Yet another Dolores clone

This is a Discord Bot for Pixel Starships, targeted for hosting on Heroku.

## Collaboration Guide

### Coding style

This repository largely follows [PEP8](https://www.python.org/dev/peps/pep-0008/) with the following differences:
* There's no [maximum line length](https://www.python.org/dev/peps/pep-0008/#maximum-line-length).

and the following changes/specifications:
* A multiline construct with brace/bracket/parenthesis has the closing brace/bracket/parenthesis alone on the last lined up under the first character of the line that starts the multiline construct (like in the last example of the PEP8 section [Indentation](https://www.python.org/dev/peps/pep-0008/#indentation)).
* Binary operators _follow_ a line break (they're first on the new line, like in the 2nd example of the PEP8 section [Should a Line Break Before or After a Binary Operator?](https://www.python.org/dev/peps/pep-0008/#should-a-line-break-before-or-after-a-binary-operator)).
* Always annotate functions, function arguments and variables in the global scope of a module (like constants). Variables in non-global scope do not have to be annotated. This will help with code inspection and completion plugins in IDEs.
* Classes should not make attributes public, but use properties so that the values may not be changed on accident (use the `@property` function decorator).

The style may vary slightly between modules. Make sure to match the general style for a given module you're working on.

### Module structure

Modules are divided into one or more sections as described below. Within these sections, functions are ordered by their visibility (public or private) and then by their name.

A section consists of a comment containing the title followed by a group of functions. There's a gap of 2 lines between the imports and the 1<sup>st</sup> section of each module. Between two subsequent sections, there's a gap of 5 line breaks.

```py
...imports...


# ---------- Section name ----------

group of functions





# ---------- Section 2 name ----------

group of functions
...
```
* **Typehint definitions**

This section contains custom typehint definitions.
* **Constants**

This section contains public and private constants. These may be initialized in the _Initialization_ section. Constants are ordered and grouped by name. Between each group there's a gap of 1 line.
* **Classes**

This section contains classes related to the module. There's a gap of 5 lines between two subsequent classes.
* **_Command_ functions**

This section contains public functions used by the bot's commands'. If a module contains functions used by multiple commands, there may be multiple **_Command_ functions** sections. These sections are named in relation to the respective command, e.g. _Fleet functions_. They also may contain any helper functions used exclusively by functions contained in this section.
* **Transformation functions**

This section contains functions used for transforming data returned by the Pixel Starships' API.
* **Helper functions**

This section contains public and private helper functions related to the module. If such functions are only being used in one specific _Command functions_ section, move the respective helper function there instead.
* **Create entity details**

This section contains boilerplate functions for creation of EntityDetails and EntityDetailsCollection objects.
* **DB**

This section may contain module-specific database functions.
* **Mocks**

This section contains code to create mockups of API data used for testing.
* **Initialization**

This section contains variables that get initialized during module setup and methods for asnyc initialization of constants and variables.


## Hosting your own copy

Check [HOSTING.md](HOSTING.md) for instructions on hosting your own copy of the bot.


## Bot Usage on Discord

The bot will fully initialize upon start.

In Discord chat, open the help using the command:

```
/help
```

As the author you can also get a list of all commands using:

```
/commands
```