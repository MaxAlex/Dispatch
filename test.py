from parsing import parse_toplevel, evaluate
from task import Context
from rendering import Renderer


if __name__ == '__main__':
    context = Context([])
    evaluate(context, parse_toplevel('new task "Do the thing" with priority 7, deadline 1/1/2021'))
    evaluate(context, parse_toplevel('new task under 1 "Do the first part of the thing" with priority 10'))
    evaluate(context, parse_toplevel('new task "Start doing first part of the thing"'))
    evaluate(context, parse_toplevel('move 3 under 2'))
    evaluate(context, parse_toplevel('new task under 1 "Do the second part of the thing" with priority 3'))
    evaluate(context, parse_toplevel('new task under 4 "Start doing second part of the thing" with deadline 12/5/2020, priority 2'))
    # print(context.toJson())
    renderer = Renderer()
    print(renderer.fullDisplay(context, 3))
