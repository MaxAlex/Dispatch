from datetime import date, datetime, timedelta
from rendering import Renderer
from collections import deque

# Name idea: YATA (Yet Another Todo Application) ?

# TODO : "duration" attribute indicating how long the task is expected
# to require in the general "working" state
# this would allow the plan summary to highlight tasks that are near/under
# their deadline-minus-duration (and incentivize using the "working" state,
# which would also enhance the plan summary.)

POSSIBLE_STATUSES = {"Open", "Working", "Done"}

class Item: # Can be Step or Task
    @staticmethod
    def fromJson(jd):
        subtasks = [Task.fromJson(subtask) for subtask in jd['subtasks']]
        steps = [Step.fromJson(step) for step in jd['steps']]
        for st in subtasks:
            st.parent = jd['num']
        for st in steps:
            st.parent = jd['num']
        if steps:
            print(steps)

        return Item(num=str(jd["num"]).strip(), statement=jd['statement'],
            deadline=date.fromordinal(jd['deadline']) if jd['deadline'] is not None else None,
            created=datetime.fromisoformat(jd['created']) if jd.get('created', None) is not None else datetime.now(),
            completed=datetime.fromisoformat(jd['completed']) if jd.get('completed', None) is not None else None,
            status=jd['status'], blocks=set(jd['blocks']), blocked_by=set(jd.get('blocked_by', [])),
            subtasks=subtasks, steps=steps,
            note=jd.get('note', ''))

    def __init__(self, num, statement, status='Open', deadline=None, created=None, completed=None,
                 duration=None, blocks=None, blocked_by=None, subtasks=None, steps=None, note=''):
        self.id = 'unused'
        self.num = num
        self.parent = None  # Parent is set during insertion, or "None" if top-level
        self.statement = statement
        self.deadline = deadline
        self.created = created
        self.completed = completed
        self.status = status
        self.duration = duration
        self.blocks = blocks if blocks is not None else set()
        self.blocked_by = blocked_by if blocked_by is not None else set()
        self.subtasks = subtasks if subtasks is not None else []
        self.steps = steps if steps is not None else []
        self.note = note

    def toJson(self):
        return {
            "id": self.id,
            "num": self.num,
            "statement": self.statement,
            "deadline": self.deadline.toordinal() if self.deadline is not None else None,
            "created": self.created.isoformat() if self.created is not None else None,
            "completed": self.completed.isoformat() if self.completed is not None else None,
            "duration": self.duration.days if self.duration is not None else None,
            "status": self.status,
            "blocks": list(self.blocks),
            "blocked_by": list(self.blocked_by),
            "subtasks": [x.toJson() for x in self.subtasks],
            "steps": [x.toJson() for x in self.steps],
            "note": self.note
        }


    # TODO better blocker handling eventually
    def getStatus(self):
        if self.status == "Done" or not self.blocked_by:
            return self.status
        else:
            return "Blocked (%s)" % ','.join(map(str, self.blocked_by))

    def setStatus(self, status):
        if status not in POSSIBLE_STATUSES:
            raise RuntimeError("Can only status to one of %s" % POSSIBLE_STATUSES)
        else:
            if status == "Done":
                self.completed = datetime.now()
                for subtask in self.subtasks:
                    subtask.setStatus("Done")
            self.status = status


    # Should this recurse into Steps?
    def getSubtaskCount(self, status=None):
        if status:
            # Does not consider blocking
            return (len([x for x in self.subtasks if x.status == status]) +
                    sum([x.getSubtaskCount(status) for x in self.subtasks]))
        else:
            return len(self.subtasks) + sum([x.getSubtaskCount() for x in self.subtasks])

    def getStepCount(self, status=None):
        if not status:
            return len(self.steps)
        else:
            return len([x for x in self.steps if x.status == status])

    def getSubtasks(self, status=None, not_status=None, recursive=False):
        if status:
            tasks = [x for x in self.subtasks if x.status == status]
        else:
            tasks = [x for x in self.subtasks if x.status != not_status]
        if recursive:
            tasks += sum([t.getActiveSubtasks(True, status=status, not_status=status) for t in tasks], [])
        return tasks


class Step(Item):
    @staticmethod
    def fromJson(jd):
        item = Item.fromJson(jd)
        item.__class__ = Step  # Janky!  But roughly valid.  Better way?
        return item

    # __init__ and toJson are identical with superclass


class Task(Item):
    @staticmethod
    def fromJson(jd):
        subtasks = [Task.fromJson(subtask) for subtask in jd['subtasks']]
        steps = [Step.fromJson(step) for step in jd['steps']]
        for st in subtasks:
            st.parent = jd['num']
        for st in steps:
            st.parent = jd['num']

        return Task(num=str(jd["num"]).strip(), statement=jd['statement'], priority=jd.get('priority', 5),
            deadline=date.fromordinal(jd['deadline']) if jd['deadline'] is not None else None,
            created=datetime.fromisoformat(jd['created']) if jd.get('created', None) is not None else datetime.now(),
            completed=datetime.fromisoformat(jd['completed']) if jd.get('completed', None) is not None else None,
            status=jd['status'], blocks=set(jd['blocks']), blocked_by=set(jd.get('blocked_by', [])),
            subtasks=subtasks, steps=steps,
            note=jd.get('note', ''))

    def __init__(self, num, statement, priority=5, **kwargs):
        self.priority = priority
        super(Task, self).__init__(num, statement, **kwargs)

    def toJson(self):
        itemjson = super(Task, self).toJson()
        itemjson["priority"] = self.priority
        return itemjson

class Context:
    def toJson(self):
        return {
            "base": [x.toJson() for x in self.baseTasks]
        }

    @staticmethod
    def fromJson(js):
        tasks = [Task.fromJson(x) for x in js["base"]]
        return Context(tasks)

    def __init__(self, basetasks):
        self.baseTasks = basetasks
        self.lookup = self.createLookup(basetasks)
        self.renderer = Renderer(self)
        self.toArchive = []

    def createLookup(self, basetasks):
        def _getIds(task):
            i = {task.num: task}
            for subtask in task.subtasks:
                i.update(_getIds(subtask))
            for step in task.steps:
                i.update(_getIds(step))
            return i

        lookup = {}
        for task in basetasks:
            lookup.update(_getIds(task))

        return lookup

    def consistencyCheck(self):
        tasks = self.lookup.values()

        for t in tasks:
            bb_ns = t.blocked_by
            for bn in bb_ns:
                b = self.lookup[bn]
                if b.status == "Done":
                    print("%d blocked by %d but latter is Done" % (t.num, bn))
                if t not in b.blocks:
                    print("%d blocked by %d but latter does not list former in blocked" % (t.num, bn))

            for subtask in t.subtasks:
                if subtask.parent != t.num:
                    print("%d has %d for child but latter does not have former as parent" % (t.num, subtask.num))

        for bt in basetask:
            if bt.parent:
                print("%d lists %d as parent but is a base task" % (bt.num, bt.parent))

    def getNextNumber(self):
        try:
            top = max(int(x.num) for x in self.lookup.values() if x.num.isdigit())
            return str(int(top) + 1)
        except ValueError:
            return 1

    def getNextStepNumber(self, parent):
        return "%s-%s" % (parent.num, len(parent.steps)+1)


    def addNew(self, newtask, parent=None):
        if parent:
            self.lookup[parent].subtasks.append(newtask)
        else:
            self.baseTasks.append(newtask)

    def addBlock(self, blocker, blockee):
        self.lookup[blocker].blocks.add(blocker)
        self.lookup[blockee].blocked_by.add(blockee)

    def setTaskStatus(self, task, status):
        assert(status in POSSIBLE_STATUSES)

        if status == "Done":
            for b_num in task.blocks:
                self.lookup[b_num].blocked_by.remove(task.num)
            for t in task.subtasks:
                self.setTaskStatus(t, "Done")

        task.status = status

    def insertStep(self, newstep, parent, index):
        self.lookup[newstep.num] = newstep
        newstep.parent = parent.num
        parent.steps.insert(index, newstep)
        # Should instead barf if it tries to add a step with out-of-order deadlines

        return self.renderer.showTasks([parent], self.lookup[parent.parent] if parent.parent else None)

    # This can be replaced with call to insertTasks, right?
    def insertTask(self, newtask, parent=None, index=None):
        self.lookup[newtask.num] = newtask
        newtask.parent = parent
        if parent:
            if not index:
                index = len(self.lookup[parent].subtasks)
            self.lookup[parent].subtasks.insert(index, newtask)
        else:
            if not index:
                index = len(self.baseTasks)
            self.baseTasks.insert(index, newtask)

        return self.renderer.showTasks([newtask], self.lookup[parent] if parent else None)

    def insertTasks(self, newtasks, parent=None, index=None):
        self.lookup.update([(t.num, t) for t in newtasks])
        for t in newtasks:
            t.parent = parent
        if parent:
            if not index:
                index = len(self.lookup[parent].subtasks)
            self.lookup[parent].subtasks = self.lookup[parent].subtasks[:index] + newtasks + self.lookup[parent].subtasks[index:]
        else:
            if not index:
                index = len(self.baseTasks)
            self.baseTasks = self.baseTasks[:index] + newtasks + self.baseTasks[index:]

        return self.renderer.showTasks(newtasks, self.lookup[parent] if parent else None)

    def popTasks(self, task_nums):
        tasks = []
        for num in task_nums:
            t = self.lookup.pop(num)
            if t.parent is not None:
                if isinstance(t, Task):
                    self.lookup[t.parent].subtasks.remove(t)
                else:
                    self.lookup[t.parent].steps.remove(t)
            else:
                self.baseTasks.remove(t)
            tasks.append(t)
        return tasks

    def show(self, task_nums, parent=None):
        tasks = [self.lookup[t] for t in task_nums]
        return self.renderer.showTasks(tasks, self.lookup.get(parent, None))

    def redoEnumeration(self):
        q = deque(self.baseTasks)
        ts = []
        while q:
            t = q.popleft()
            q.extend(t.subtasks)
            ts.append(t)
        assert(len(ts) == len(self.lookup))
        updates = {t.num: i for i, t in enumerate(ts, start=1)}
        for t in ts:
            t.num = updates[t.num]
            if t.parent:
                t.parent = updates[t.parent]
        self.lookup = self.createLookup(self.baseTasks)


