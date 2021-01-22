from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from parsing import parse_toplevel, evaluate, CommandException
from task import Context
import sys, os
import json
import shutil
import traceback

# POSSIBLE CODE SMELLS:
# - Nonpythonic functionality in eval functions with their multiple "returns"
#       Have eval functions store output in "to print" var in Renderer, which is rendered by an outer print step?
# - Renderer being owned by but also pointing to context is weird
#       Renderer needs context because : getting task info
#       context needs Renderer because : want to call rendering functions from within eval steps
# - Should be configurable!
# - "sparkle" coloring is going to annoy people

SAVE_FILE = '/home/zake/.todo/tasks.json'  # TODO make better, also configurable?
ARCHIVE_FILE = '/home/zake/.todo/archive'
REPL_HISTORY_FILE = '/home/zake/.todo/repl_hist'


def execute(context, cmd):
    try:
        out = evaluate(context, parse_toplevel(cmd))
        print(out.replace('\n', '\n '))
    except CommandException as err:
        print(str(err))
    # except Exception as err:
    #     traceback.print_exc()

def repl(context):
    session = PromptSession(history=FileHistory(REPL_HISTORY_FILE))
    print("\n\t<<<As-Yet-Unnamed Todo App>>>\n\nType 'q' to quit; type ? if confused, but it won't help\n")
    while (cmd := session.prompt('==> ')).strip() not in {'exit', 'q', ':q!'}:
        execute(context, cmd)


if __name__ == '__main__':
    cmd = " ".join(sys.argv[1:]).strip()

    if not os.path.exists(SAVE_FILE):
        print("Making new todo file at %s" % SAVE_FILE)
        stub = Context([]).toJson()
        with open(SAVE_FILE, 'w') as out:
            json.dump(stub, out)

    context = Context.fromJson(json.load(open(SAVE_FILE, 'r')))
    if cmd:
        print("==> %s" % cmd)
        execute(context, cmd)
    else:
        repl(context)

    with open(ARCHIVE_FILE, 'a') as arch_out:
        print("Writing %d to archive" % len(context.toArchive))
        arch_out.write('\n'.join([json.dumps(t.toJson()) for t in context.toArchive]) + '\n')
    newjson = context.toJson()
    with open(SAVE_FILE + '.writing', 'w') as out:
        json.dump(newjson, out)
    shutil.move(SAVE_FILE + '.writing', SAVE_FILE)
