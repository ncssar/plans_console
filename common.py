# common.py - variables shared by all modules in the plans_console import tree
# define default values here; will be overridden by modules that import this module
# https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules

import os
import sys

pcDir='C:\\PlansConsole'
logfile=None # so that sartopo_bg can determine if the calling module has already set the logfile