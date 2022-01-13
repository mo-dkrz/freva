"""Collection of utilities of the freva command line argument parser."""

from __future__ import annotations
import argparse
from copy import copy
from getpass import getuser
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import sys

from evaluation_system.misc import config, logger
from evaluation_system.misc.exceptions import CommandError, hide_exception


def is_admin(raise_error: bool = False) -> bool:
    """Check if the user at runtime is one of the admins.

    Parameters:
    -----------
    raise_error:
        Raise a RuntimeError if user is not admin
    """
    config.reloadConfiguration()
    admin = config.get("admins", [])
    user = getuser()
    if isinstance(admin, str):
        admin = [admin]
    is_admin = user in admin
    if not is_admin and raise_error:
        raise RuntimeError(f"{user} is not in admin list")
    return is_admin


class BaseParser:
    """Base class for common command line argument parsers."""

    def __init__(
        self, sub_commands: Dict[str, str], parser: argparse.ArgumentParser
    ) -> None:
        """Create the sub-command parsers."""

        self.parser = parser
        self.subparsers = parser.add_subparsers(help="Available sub-commands:")
        self.sub_commands = sub_commands
        for command in sub_commands.keys():
            getattr(self, f"parse_{command.replace('-','_')}")()

    @property
    def logger(self) -> logging.Logger:
        """Use evaluation_system logger in all classes using ths class."""
        return logger

    def set_debug(self, debug: bool) -> None:
        """Set the logger level to DEBUG."""
        if debug is True:
            self.logger.setLevel(logging.DEBUG)

    def parse_args(self, argv: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse the command line arguments."""
        args = self.parser.parse_args(argv or None)
        self.kwargs = {k: v for (k, v) in args._get_kwargs() if k != "apply_func"}
        self.set_debug(self.kwargs.pop("debug", False))
        return args

    @classmethod
    def get_subcommands(cls) -> Dict[str, str]:
        """Create the available sub commands for a user."""
        sub_commands = {
            "databrowser": "Find data in the system.",
            "plugin": "Apply data analysis plugin.",
            "history": "Read the plugin application history.",
            "crawl-my-data": "Update users project data",
            "esgf": "Search/Download ESGF the data catalogue.",
        }
        admin_commands = {
                "solr": "Apache solr server related sub-commands.",
                "check": "Perform various checks.",
                "doc": "Update the plugin documentation."
        }
        if is_admin():
            return {**sub_commands, **admin_commands}
        return sub_commands

    def _usage(self, *args: Optional[Any], **kwargs: Optional[Any]) -> None:
        """Exit with usage message."""
        self.parser.error(
            "the following sub-commands are "
            f"required: {', '.join(self.sub_commands)}"
        )


class BaseCompleter:
    """Base class for command line argument completers."""

    def __init__(self,
                 metavar: str,
                 choices: Optional[Dict[str, Tuple[str, str]]] = None,
                 shell: str = "bash",
                 argv: List[str] = [],
                 strip: bool = False,
                 flags_only: bool = True):
        self.choices = choices or {}
        self.strip = strip
        self.metavar = metavar
        self.argv = argv
        self.flags_only = flags_only
        if shell == "zsh":
            self.get_print = self._print_zsh
        elif shell == "fish":
            self.get_print = self._print_fish
        else:
            self.get_print = self._print_default

    def _print_zsh(self, choices: Dict[str, Tuple[str, str]]) -> List[str]:
        out = []
        for key, (help, func) in choices.items():
            if self.metavar != "databrowser" or key.startswith('-'):
                out.append(f"{key}[{help}]{func}")
            else:
                out.append(f"{key}: {help}")
        return out

    def _print_fish(self, choices: Dict[str, Tuple[str, str]]) -> List[str]:
        out = []
        for key, (help, func) in choices.items():
            out.append(f"{key}: {help}")
        return out

    def _print_default(self, choices: Dict[str, Tuple[str, str]]) -> List[str]:

        out = []
        for key, (help, func) in choices.items():
            if self.metavar == "databrowser" and not key.startswith("-"):
                out.append(f"{key}: {help}")
            else:
                out.append(key)
        return out

    def _get_databrowser_choices(self) -> Dict[str, Tuple[str, str]]:
        """Get the choices for databrowser command."""
        from freva import databrowser
        facet_args = []
        for arg in self.argv:
            try:
                key, value = arg.split("=")
            except ValueError:
                continue
            if value and key:
                facet_args.append(arg)
        facets = BaseCompleter.arg_to_dict(facet_args)
        search = databrowser(attributes=False, all_facets=True, **facets)
        choices = {}
        for att, values in search.items():
            keys = ",".join([v for n, v in enumerate(values)])
            choices[att] = (keys, "")
        return choices

    def _get_plugin_choices(self) -> Dict[str, Tuple[str, str]]:
        """Get the choices for the plugin command."""
        from freva._plugin import list_plugins
        from evaluation_system.api import plugin_manager as pm

        docs: Dict[str, Dict[str, str]] = {}
        desc: Dict[str, Dict[str, str]] = {}
        plugins: Dict[str, str] = {}
        for plugin in list_plugins():
            parameters = pm.getPluginInstance(plugin).__parameters__
            plugins[plugin] = pm.getPluginInstance(plugin).__short_description__
            docs[plugin] = dict(parameters.items())
            desc[plugin] = {}
            for key, param in parameters._params.items():
                if param.mandatory:
                    desc[plugin][key] = f"{param.help} (mandatory)"
                else:
                    desc[plugin][key] = f"{param.help} (default: {docs[plugin][key]})"
        args = [arg for arg in self.argv if not arg.startswith('-') and arg != "plugin"]
        choices = {}
        if not args:
            # No plugin name was given
            return {pl: (help, "") for pl, help in plugins.items()}
        try:
            config = docs[args[0]]
            setup = desc[args[0]]
        except KeyError:
            # Wrong plugin name
            return {}
        options = []
        for key in config.keys():
            option_present = False
            for arg in args:
                if arg.startswith(f"{key}="):
                    option_present = True
                    break
            if not option_present:
                options.append(f"{key}=")
        for option in options:
            opt = option.strip("=")
            if "file" in setup[opt].lower() or "dir" in setup[opt].lower():
                choices[opt] = (setup[opt], ":file:_files")
            else:
                choices[opt] = (setup[opt], "")
        return choices

    @property
    def command_choices(self) -> Dict[str, Tuple[str, str]]:

        choices = {}
        if self.flags_only:
            return self.choices
        if self.metavar == "databrowser":
            choices = self._get_databrowser_choices()
        elif self.metavar == "plugin":
            choices = self._get_plugin_choices()
        return {**self.choices, **choices}

    def formated_print(self) -> None:
        """Print all choices to be processed by the shell completion function."""

        out = self.get_print(self.command_choices)
        for line in out:
            if line.startswith("-") and self.strip and not self.flags_only:
                continue
            print(line)

    @staticmethod
    def arg_to_dict(args: List[str], append: bool = False) -> Dict[str, List[str]]:
        """Convert a parsed arguments with key=value pairs to a dictionary.

        Parameters:
        ----------
        args:
            Collection of arguments that are converted to dict, the arguments
            should be of form key=value
        append:
            If a key occurs twice convert first value to list and append second
            value to list, the default behaviour is updating the entry with
            the second value
        Returns:
        --------
        dict: Dictionariy representation of key=value pairs
        """
        out_dict: Dict[str, List[str]] = {}
        for arg in args:
            try:
                key, value = arg.split("=")
            except ValueError:
                with hide_exception():
                    raise CommandError(f"Bad Option: {arg}")
            if append and key in out_dict:
                out_dict[key].append(value)
            else:
                out_dict[key] = [value]
        return out_dict

    def _to_dict(self, parsed_args: argparse.ArgumentParser) -> Dict[str, List[str]]:
        args = getattr(parsed_args, self.metavar)
        return self.arg_to_dict(args)

    def __call__(self, **kwargs: Optional[str]) -> Optional[List[str]]:
        return list(self.choices.keys())

    @staticmethod
    def _get_choices_from_parser(
            parser: argparse.ArgumentParser
    ) -> Dict[str, Tuple[str, str]]:

        choices = {}
        for action in parser._actions:
            action_type = ""
            if action.type == Path:
                action_type = ":file:_files"
            if action.option_strings:
                choice = action.option_strings[0]
            else:
                choice = action.dest
            if choice not in ("facet", "facets", "tool-name", "options"):
                choices[choice] = (action.help or "", action_type)
        return choices

    @classmethod
    def get_args_of_subcommand(cls, argv: List[str]) -> Dict[str, Tuple[str, str]]:
        """Get all possible arguments from a freva sub-command."""
        sub_command = argv.pop(0)
        sub_mod = sub_command.replace("-", "_")
        try:
            mod = __import__(f"freva.cli.{sub_mod}", fromlist=[""])
            CliParser = getattr(mod, mod.CLI)()
            return cls._get_choices_from_parser(CliParser.parser)
        except ImportError:
            mod = __import__(f"freva.cli.admin.{sub_command}", fromlist=[""])
        # Admin parsers are sub command parsers and need a parent parser
        parent_parser = argparse.ArgumentParser()
        CliParser = getattr(mod, mod.CLI)(parent_parser)
        sub_cmds = {k: (v, "") for (k, v) in CliParser.sub_commands.items()}
        if not argv:
            # Only the 1st admin sub command was given:
            return sub_cmds
        # Get the choices for the 2nd sub command
        next_cmd = argv.pop(0).replace('-', '_')
        try:
            NewParser = getattr(CliParser, f"parse_{next_cmd}")()
        except AttributeError:
            return {}
        return cls._get_choices_from_parser(NewParser.parser)

    @classmethod
    def parse_choices(cls, argv: List[str] = sys.argv[1:]) -> BaseCompleter:
        """Create the completion choices from given cmd arguments."""
        parser = argparse.ArgumentParser(
                description="Get choices for command line arguments"
        )
        parser.add_argument("command",
                            help="First command, freva, freva-histor etc",
                            type=str)
        parser.add_argument("--shell",
                            help="Shell in use",
                            default="bash",
                            type=str)
        parser.add_argument("--strip",
                            help="Do not print options starting with -",
                            default=False,
                            action="store_true")
        parser.add_argument("--flags-only",
                            help="Only print options starting with -",
                            default=False,
                            action="store_true")
        ap, args = parser.parse_known_args(argv)
        main_choices = {k: (v, "") for k, v in BaseParser.get_subcommands().items()}
        if ap.command == "freva" and not args:
            return cls(ap.command, main_choices, shell=ap.shell, strip=ap.strip)
        elif ap.command != "freva":
            sub_cmd = "-".join(ap.command.split("-")[1:])
            args.insert(0, sub_cmd)
        choices = {}
        if args[0] in main_choices:
            choices = cls.get_args_of_subcommand(copy(args))
        choices = {k: v for (k, v) in choices.items() if k not in args}
        return cls(args[0],
                   choices,
                   shell=ap.shell,
                   argv=args,
                   strip=ap.strip,
                   flags_only=ap.flags_only)
