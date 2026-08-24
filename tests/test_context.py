from agent_replay import context
from agent_replay.schema import Run


def _frame(run_id):
    return context.TraceFrame(run=Run(run_id=run_id, agent_name="a"), store=None, redaction=None)


def test_stack_push_pop_and_current():
    assert context.current_frame() is None
    assert context.depth() == 0

    f1 = _frame("run_1")
    context.push_frame(f1)
    assert context.depth() == 1
    assert context.current_frame() is f1

    f2 = _frame("run_2")
    context.push_frame(f2)
    assert context.current_frame() is f2
    assert context.depth() == 2

    assert context.pop_frame() is f2
    assert context.current_frame() is f1
    assert context.pop_frame() is f1
    assert context.current_frame() is None
    assert context.pop_frame() is None
