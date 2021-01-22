from datetime import date, datetime
import colors as c


# from colorama import Fore, Back, Style
# class Color:
#     # Priority levels (ideally shouldn't connote goodness-badness)
#     LOW = Fore.BLUE + Style.DIM
#     MIDLOW = Fore.WHITE + Style.DIM
#     MID = Fore.WHITE
#     MIDHIGH = Fore.WHITE + Style.BRIGHT
#     HIGH = Fore.YELLOW + Style.BRIGHT
#     VERYHIGH = Fore.RED + Style.BRIGHT
#     OVERHIGH = Fore.RED + Back.MAGENTA + Style.BRIGHT
#
#     # Warning levels (ideally shouldn't connote importance)
#     NOWORRIES = Fore.CYAN + Style.DIM
#     VERYGOOD = Fore.CYAN + Style.BRIGHT
#     GOOD = Fore.GREEN
#     NOTICE = Fore.YELLOW + Style.BRIGHT
#     ALERT = Fore.RED + Style.BRIGHT
#     VERYALERT = Fore.RED + Back.MAGENTA
#
#     def p(self, mode, text):
#         return self.__getattribute__(mode) + text + Style.RESET_ALL

def intuitiveDate(d):
    daysUntil = (d - date.today()).days
    if daysUntil == -1:
        return "YESTERDAY"
    elif daysUntil == 0:
        return "TODAY"
    elif daysUntil == 1:
        return "tomorrow"
    elif daysUntil == 2:
        return "day-after-tomorrow"  # "overmorrow"?
    else:
        return str(d)

def _allmin(items, key=lambda x: x):
    agg = []
    least = key(items[0])
    for i in items:
        if key(i) == least:
            agg.append(i)
        elif key(i) < least:
            agg = [i]
    return agg


class Renderer:
    # TODO Renderer will keep track of screen properties
    def __init__(self, context):
        self.context = context

    # TODO color thresholds should be configurable
    # TODO alternately, thresholds should be set based on the priorities that are in use!
    @staticmethod
    def priorityColors(priority, text, done=False):
        if done:
            return c.PRIORITY_DONE(text)
        if priority is None or priority <= 0:
            return c.LOWEST(text)
        elif priority < 2:
            return c.LOW(text)
        elif priority <= 4:
            return c.MIDLOW(text)
        elif priority <= 7:
            return c.MID(text)
        elif priority == 8:
            return c.MIDHIGH(text)
        elif priority == 9:
            return c.HIGH(text)
        elif priority >= 10:
            return c.HIGHEST(text)
        else:
            raise RuntimeError(priority)

    @staticmethod
    def statusColors(text):
        if text == "Open":
            return c.OPEN(text)
        elif text == "Working":
            return c.WORKING(text)
        elif text == "Done":
            return c.DONE(text)
        else:
            return c.BLOCKED(text)

    @staticmethod
    def dateColors(dateval, text):
        if dateval is None:
            return c.DISTANT(text)
        else:
            daydiff = (dateval - datetime.now().date()).days
            if daydiff >= 30:
                return c.DISTANT(text)
            elif 30 > daydiff >= 7:
                return c.LATER(text)
            elif 7 > daydiff >= 2:
                return c.SOON(text)
            elif 2 > daydiff >= 0:
                return c.IMPENDING(text)
            elif daydiff < 0:
                return c.OVERDUE(text)


    @staticmethod
    def renderDeadline(dl):
        if dl is None:
            return Renderer.dateColors(None, "No deadline")
        else:
            daydiff = (dl - datetime.now().date()).days
            if daydiff >= 0:
                return Renderer.dateColors(dl, f"Due {intuitiveDate(dl)}")
            else:
                return Renderer.dateColors(dl, f"Overdue from {intuitiveDate(dl)}")

    def itemInfo(self, item, include_sub=False):
        if hasattr(item, 'priority'):
            prioritySegment = self.priorityColors(item.priority, str(item.priority))
        else:
            prioritySegment = None

        statusSegment = self.statusColors(item.getStatus())

        if item.deadline is None:
            deadlineSegment = None
        else:
            deadlineSegment = self.renderDeadline(item.deadline)

        if include_sub and (stc := item.getSubtaskCount()):
            subtaskSegment = "%s/%s subtasks" % (item.getSubtaskCount("Done"), stc)
        else:
            subtaskSegment = None

        if include_sub and (sc := item.getStepCount()):
            stepSegment = "%s/%s steps" % (item.getStepCount("Done"), sc)
        else:
            stepSegment = None

        if item.duration is None:
            durationSegment = None
        else:
            durationSegment = f"{item.duration.days} days"

        if include_sub and item.note:
            noteSegment = c.NOTE("Note")
        else:
            noteSegment = None


        return ' - '.join([x for x in [prioritySegment, statusSegment, deadlineSegment,
                                       durationSegment, stepSegment, subtaskSegment]
                           if x is not None])


    # IND_PLACEHOLD = 'INDENTATION!'
    # # renderTree handles overall tree structure, and calls renderTask and renderStep for
    # # individual Task/Step lines (which can themselves be multilines, for notes and etc)
    # # This also handles tree-structure indentation!
    # def renderTree(self, baseitem, levels, include_done=False):
    #     lines = renderTask(baseitem) if

    def renderStep(self, step):
        return f'{step.num}. {step.statement} - {self.itemInfo(step, include_sub=True)}'

    # Task renderer behavior dependent on "level", which decreases as one goes
    # into sub-tasks
    # 0 - just show number, statement, and status, all in one line
    # 1 - show number+statement line, deadline+status+subtask-count line
    # 2 - show number+statement line, deadline+status line, subtask lines (at -1 priority)
    # 3+ - as 2
    def renderTask(self, task, level=0, indent=0, include_done=False):
        indentstr = '   '*indent

        if level <= 0:
            return '{ind}#{num}. {statement}  { {info} }'.format(
                ind=indentstr, num=task.num, statement=self.priorityColors(task.priority, f'"{task.statement}"'),
                info=self.itemInfo(task, include_sub=True)
            )
        else:
            subtasks = "\n".join([self.renderTask(t, level-1, indent=indent+1) for t in task.subtasks
                                  if (include_done or t.getStatus() != 'Done')])
            substeps = f"\n".join([f"{indentstr}       | " + self.renderStep(s) for s in task.steps]) + '\n'
            
            # TODO once Renderer is made aware of screen size, properly right-justify this?
            if task.note:
                if ('\n' in task.note.strip()) or len(task.note.split('\n')[0]) >= 60:
                    notestub = task.note.split('\n')[0][:55] + "[...]"
                else:
                    notestub = task.note.strip()
                noteline = c.NOTE((' '*(80-len(notestub)))+notestub)
            else:
                noteline = ""

            if hasattr(task, 'priority'):
                statement_str = self.priorityColors(task.priority, f'"{task.statement}"')
            else:
                statement_str = task.statement

            return '{ind}#{num}. {statement} {{ {info} }} \n{noteline}{substeps}{subtasks}'.format(
                ind=indentstr, num=task.num, statement=statement_str,
                info=self.itemInfo(task), noteline=noteline,
                substeps='\n'+substeps if task.steps else "",
                subtasks='\n'+subtasks if subtasks else ""
            )

    def summary(self):
        openTasks = [x for x in self.context.lookup.values() if hasattr(x, 'priority') and x.getStatus() != "Done"]
        # highestp = max(openTasks, key=lambda x: x.priority)
        highestp = min(_allmin(openTasks, key=lambda x: -x.priority if x.priority is not None else date.max),
                       key=lambda x: x.deadline if x.deadline is not None else date.max)
        countLine = "{tasks} tasks open, highest priority is {num} ({p})".format(
            tasks=len(openTasks),
            num=self.priorityColors(highestp.priority, '#'+str(highestp.num)),
            p=self.priorityColors(highestp.priority, str(highestp.priority))
        )

        dltasks = [x for x in openTasks if x.deadline]
        if dltasks:
            # soonest = min(dltasks, key=lambda x: x.deadline)
            soonest = max(_allmin(dltasks, key=lambda x: x.deadline), key=lambda x: x.priority)
            dlLine = ", nearest deadline is {num} ({dl})".format(
                num=self.priorityColors(soonest.priority, '#'+str(soonest.num)),
                dl=self.dateColors(soonest.deadline, intuitiveDate(soonest.deadline)))
        else:
            dlLine = ""



        return countLine + dlLine

    def taskDetails(self, task, parent = None):
        if parent is None:
            pline = ""
        else:
            pline = f"Parent: #{parent.num}. {parent.statement}\n"

        is_done = task.getStatus() == "Done"
        if task.duration:
            if task.deadline:
                start_within = (task.deadline - task.duration) - date.today()
                start_str = self.priorityColors(9-start_within.days, "(start within %d days)" % start_within.days)
            else:
                start_str = ""
            duration_str = f"{task.duration.days} days " + start_str
        else:
            duration_str = "None"

        lines = [pline,
                 f'#{task.num}. "{self.priorityColors(task.priority, task.statement, is_done)}"',
                 f"\tPriority: {self.priorityColors(task.priority, str(task.priority), is_done)}",
                 f"\tStatus: {self.statusColors(task.getStatus())}",
                 f"\tDeadline: {c.DONE(str(task.deadline)) if is_done else self.dateColors(task.deadline, str(task.deadline))}",
                 f"\tExpected duration: {duration_str}",
                 f"\tCreated: {task.created.isoformat(sep=' ', timespec='minutes')}",
                 f"\tBlocks: {','.join(map(str, task.blocks))}",
                 f"\tBlocked by: {','.join(map(str, task.blocked_by))}"]

        if task.getStatus() == "Done":
            lines.append(f"\tCompleted: {task.completed.isoformat(sep=' ', timespec='minutes')}")

        if task.steps:
            steplines = ["\t\t" + f'{st.num}. {st.statement} - {st.status}' for st in task.steps]
            lines.append(f"\n\t{len(task.steps)} steps:\n" + '\n'.join(steplines))

        active_subtasks = task.getSubtasks(not_status="Done", recursive=False)
        if active_subtasks:
            subtasklines = []
            for st in active_subtasks:
                subtasklines.append("\t\t" + f'#{st.num}. "{self.priorityColors(st.priority, st.statement)}"')
            lines.append(f"\n\t{len(active_subtasks)} subtasks:\n" + '\n'.join(subtasklines))

        closed_subtasks = task.getSubtasks(status="Done", recursive=False)
        if closed_subtasks:
            subtasklines = []
            for st in closed_subtasks:
                subtasklines.append("\t\t" + c.DONE(f'#{st.num}. "{st.statement}"'))
            lines.append(f"\n\t{len(closed_subtasks)} completed subtasks:\n" + '\n'.join(subtasklines))

        if task.note:
            lines.append("\n\tNote:\n\t%s" % c.NOTE(task.note.replace('\n', '\n\t')))

        return '\n'.join(lines)

    def fullDisplay(self, depth, include_done=False):
        tasks = sorted(self.context.baseTasks, key=lambda x: x.priority)
        tasklines = '\n'.join([self.renderTask(x, level=depth, include_done=include_done) for x in tasks
                               if (include_done or x.getStatus() != 'Done')])
        # return "\n\n".join([tasklines, self.summary(context)]) + "\n"
        return "\n%s\n\n%s\n" % (tasklines, self.summary())

    def showTasks(self, tasks, parent = None):
        if parent is None:
            pline = ""
        else:
            pline = f"Parent: #{parent.num}. {parent.statement}\n"

        return '\n'.join([pline] + [self.renderTask(t, level=10, indent=(1 if parent else 0)) for t in tasks])

