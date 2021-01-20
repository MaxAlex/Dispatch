from task import Task, POSSIBLE_STATUSES
import re
from collections import namedtuple
from datetime import date, timedelta, datetime
import subprocess
import tempfile

# Command examples:
# Add new task: "new task "Do the thing" with priority 7, deadline 1/1/2020"
# Add new subtask: "new task under 321 "Do the subthing" with priority 0, deadline tomorrow"
# Add new sibling task: "new task after 321 "Do the other thing" .." (or "before")
# Move task: "move task 100 under 321" (or after/before, matching add)
# Set task attributes: "set task 321 deadline 1/1/2020, priority 1"
# Change task status: "mark task 100 Done"
# Add block: "task 100 blocks 321" (support multiple: "task 100 blocks 101, 102,103")
# ("task" should be an optional word in all of these, I think)


class CommandException(Exception):
    pass

def eval_new(context, attributes, referent, location):
    # num = context.getNextNumber()
    created_at = datetime.now()
    task = Task(num=context.getNextNumber(), created=created_at, **dict(attributes))
    if location == 'before':
        reftask = context.lookup[referent]
        parent = reftask.parent
        return context.insertTask(task, parent, parent.subtasks.index(reftask))
    elif location == 'after':
        reftask = context.lookup[referent]
        parent = reftask.parent
        return context.insertTask(task, parent, parent.subtasks.index(reftask)+1)
    elif location == 'under' or (location is None and referent is None):
        return context.insertTask(task, referent)
    else:
        raise CommandException("Invalid relative specification: '%s' and '%s'" % (location, referent))

def eval_move(context, task_nums, referent, location):
    tasks = context.popTasks(task_nums)

    if location == 'before':
        reftask = context.lookup[referent]
        parent = reftask.parent
        return context.insertTasks(tasks, parent, parent.subtasks.index(reftask))
    elif location == 'after':
        reftask = context.lookup[referent]
        parent = reftask.parent
        return context.insertTasks(tasks, parent, parent.subtasks.index(reftask)+1)
    elif location == 'under' or (location is None and referent is None):
        return context.insertTasks(tasks, referent)
    else:
        raise CommandException("Invalid relative specification: '%s' and '%s'" % (location, referent))


def eval_set(context, task_nums, attributes):
    for n in task_nums:
        task = context.lookup[n]
        for att, val in attributes:
            if att == 'status':
                context.setTaskStatus(task, val)
            else:
                task.__setattr__(att, val)
    return context.show(task_nums)


def eval_block(context, task_nums, ref_task_nums):
    for n in task_nums:
        task = context.lookup[n]
        task.blocks.update(ref_task_nums)
    return context.show(task_nums)


def eval_show(context, tasks=None):
    if tasks is None:
        return context.renderer.fullDisplay(10)
    else:
        raise NotImplementedError()


def eval_showdetails(context, tasks):
    details = []
    for t_num in tasks:
        t = context.lookup[t_num]
        p = context.lookup[t.parent] if t.parent else None
        details.append(context.renderer.taskDetails(t, p))
    return '\n\n'.join(details)

def eval_note(context, task):
    with tempfile.NamedTemporaryFile(mode='r', delete=True) as tf:
        subprocess.call(['nano', tf.name])
        note = tf.read().strip()

    context.lookup[task].note = note
    return context.show([task])

def eval_cleanup(context, tasks, reorder):
    if tasks == 'all':
        tasks = [n for n, t in context.lookup.items() if t.getStatus() == "Done"]
    # if reorder:
    #     return "cleaning %s and reodering" % tasks
    # else:
    #     return "just cleaning %s" % tasks
    context.toArchive += context.popTasks(tasks)
    if reorder:
        context.redoEnumeration()
    return "Cleaned %d tasks" % len(tasks)

def eval_plan(context, task_scope, attribute):
    if task_scope is None:
        task_scope = context.baseTasks
    tasks = set(sum([t.getSubtasks(not_status="Done", recursive=True) for t in task_scope], []))

    if attribute:
        raise CommandException("NotImplementedError !")
    else:
        raise NotImplementedError

def evaluate(context, command):
    if command.type == "add_new":
        return eval_new(context, command.attributes, command.ref_task, command.location)
    elif command.type == "move":
        return eval_move(context, command.tasks, command.ref_task, command.location)
    elif command.type == "set":
        return eval_set(context, command.tasks, command.attributes)
    elif command.type == "block":
        return eval_block(context, command.tasks, command.ref_tasks)
    elif command.type == "show":
        return eval_show(context, command.tasks)
    elif command.type == "show_details":
        return eval_showdetails(context, command.tasks)
    elif command.type == "note":
        return eval_note(context, command.tasks[0])
    elif command.type == "cleanup":
        return eval_cleanup(context, command.tasks, command.arg)
    elif command.type == "plan":
        return eval_plan(context, command.tasks, command.arg)
    else:
        raise CommandException("Command parsed to an invalid command representation: %s" % command)





# ATTRIBUTE = """(?P<att_name>{attribute_list}) (?<att_value>{attribute_matcher})""".format(
#     attribute_list='|'.join(attributes), attribute_matcher="|".join(attribute_regexes)
# )


ATT_PRIORITY = """priority ([0-9]+)"""
ATT_DEADLINE = """deadline (today|tomorrow|next week|[0-9]{,2}/[0-9]{,2}/[0-9]{,4})"""
ATT_STATUS = """status (%s)""" % ('|'.join(POSSIBLE_STATUSES))
ATT_DURATION = """duration ([0-9]+ weeks|[0-9]+ days)"""

REL_LOC_CLAUSE = """((?P<location>under|before|after) (?P<loc_ref>[0-9]+))"""
MULTITASK_CLAUSE = "(?P<tasks>[0-9,]+)"

NEW = """new\s*(task)?\s*%s?\s*(?P<statement>".*")( with )?(?P<attributes>.*)?""" % REL_LOC_CLAUSE
MOVE = """move\s*(task)?\s*(?P<moved_t>[0-9]+)\s*%s""" % REL_LOC_CLAUSE
SET = """set\s*(task)?\s*(?P<tasks>[0-9, ]+)\s*(?P<attributes>.*)?"""
BLOCK = """(task)?\s*(?P<blockers>[0-9, ]+)\s*blocks\s*(?P<blockees>[0-9, ]+)"""
SHOW = """show\s*(?P<tasks>[0-9, ]+)?\s*(?P<details>details)?"""  # TODO more show options
NOTE = """annotate\s*(?P<task>[0-9]+)"""
CLEANUP = """cleanup\s*(?P<tasks>([0-9, ]+|all))\s*(?P<reorder>and reorder)?"""
PLAN = """plan\s*(?P<target>task [0-0, ]+)\s*(by)?\s(?P<attribute>(newest|oldest|deadline|priority))"""

Command = namedtuple('Command', ['type', 'task', 'tasks', 'ref_task',
                                 'ref_tasks', 'attributes', 'location',
                                 'arg'],
                     defaults=[None]*8)


def resolve_time(string):
    if string == "today":
        return date.today()
    elif string == "tomorrow":
        return date.today() + timedelta(days=1)
    elif string == "next week":
        return date.today() + timedelta(days=7)
    elif string == "next month":
        return date.today() + timedelta(days=30)  # TODO month lengths???
    else:
        # Assume month/day/year
        # TODO that should be a setting! (Or just done the other way)
        month, day, year = string.split('/')
        return date(int(year), int(month), int(day))


def parse_attribute(att_string):
    if m := re.match(ATT_PRIORITY, att_string):
        return "priority", int(m.group(1))
    elif m := re.match(ATT_DEADLINE, att_string):
        datestring = m.group(1).strip()
        return "deadline", resolve_time(datestring)
    elif m := re.match(ATT_STATUS, att_string):
        stat = m.group(1).strip()
        try:
            stat = [x for x in POSSIBLE_STATUSES if x.lower() == stat.lower()][0]
        except IndexError:
            raise CommandException("'%s' is not a valid task status" % stat)
        return "status", stat
    elif m := re.match(ATT_DURATION, att_string):
        num, unit = m.group(1).strip().split()
        if unit == "days":
            return "duration", timedelta(days=int(num))
        elif unit == "weeks":
            return "duration", timedelta(weeks=(num)*7)
        else:
            raise CommandException("Could not parse duration: %s" % m.group(1))
    else:
        raise CommandException("Could not parse '%s'; expected priority, deadline, duration, or status setting" % att_string)


def parse_toplevel(command):
    if newcmd := re.match(NEW, command):
        statement = newcmd.group("statement").strip('"')
        loc_rel = newcmd.group("location")
        loc_ref = int(n) if (n := newcmd.group("loc_ref")) is not None else None
        attributes = [parse_attribute(x.strip()) for x in newcmd.group("attributes").split(',') if x.strip()]
        attributes.append(("statement", statement))
        if len(attributes) != len(set(att_types := [x[0] for x in attributes])):
            raise CommandException("Duplicated task attributes: %s" %
                               ', '.join([x for x in set(att_types) if att_types.count(x) > 1]))
        return Command("add_new", attributes=attributes, ref_task=loc_ref, location=loc_rel)
    elif movcmd := re.match(MOVE, command):
        moved_t = [int(x) for x in movcmd.group("moved_t").split(',')]
        ref_t = int(n) if (n := movcmd.group("loc_ref")) is not None else None
        loc_rel = movcmd.group("location")
        return Command("move", tasks=moved_t, ref_task=ref_t, location=loc_rel)
    elif setcmd := re.match(SET, command):
        tasks = [int(x) for x in setcmd.group("tasks").split(',')]
        attributes = [parse_attribute(x.strip()) for x in setcmd.group("attributes").split(',') if x.strip()]
        return Command("set", tasks=tasks, attributes=attributes)
    elif blockcmd := re.match(BLOCK, command):
        blockers = [int(x) for x in blockcmd.group("blockers").split(',')]
        blockees = [int(x) for x in blockcmd.group("blockees").split(',')]
        return Command("block", tasks=blockees, ref_tasks=blockers)  # ref_tasks block tasks
    elif showcmd := re.match(SHOW, command):
        if (taskstr := showcmd.group("tasks")) is not None:
            tasks = [int(n) for n in taskstr.split(',')]
        else:
            tasks = None
        details = showcmd.group("details") is not None
        if details:
            return Command("show_details", tasks=tasks)
        else:
            return Command("show", tasks=tasks)
    elif notecmd := re.match(NOTE, command):
        task = int(notecmd.group("task").strip())
        return Command("note", tasks=[task])
    elif cleancmd := re.match(CLEANUP, command):
        taskstr = cleancmd.group("tasks")
        if taskstr == "all":
            tasks = "all"
        else:
            tasks = [int(n) for n in taskstr.split(',')]
        return Command("cleanup", tasks=tasks, arg=cleancmd.group("reorder"))
    elif plancmd := re.match(PLAN, command):
        if task_str := plancmd.group("target"):
            tasks = [int(t) for t in task_str.strip("task ").split(',')]
        else:
            tasks = None
        attribute = plancmd.group("attribute")
        return Command("plan", tasks=tasks, arg=attribute)
    else:
        raise CommandException("Could not parse: %s" % command)




if __name__ == '__main__':
    test_commands = ['new task "Do the thing" with priority 7, deadline 1/1/2020',
                     'new task under 321 "Do the subthing" with priority 0, deadline tomorrow',
                     'new task after 321 "Do the other thing"',
                     'move task 100 under 321',
                     'set task 321 deadline 1/1/2020, priority 1',
                     'task 100 blocks 321',
                     '100,101,103 blocks 201,202,303']

    for cmd in test_commands:
        print(parse_toplevel(cmd))
    print("Done.")