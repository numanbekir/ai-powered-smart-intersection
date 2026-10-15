"""Runs the simulation window in its own process.

The simulation window (pygame) and the main window (Tkinter) cannot share
a process: once a simulation window has been opened and closed, creating
new Tkinter input fields crashes the interpreter.
"""
import multiprocessing


def _run(connection, language, engine_arguments):
    import core.i18n as i18n
    from simulation.engine import SimulationEngine

    # The window runs in a fresh process, so the language chosen in the
    # main window has to be passed on.
    i18n.set_language(language)

    try:
        while True:
            outcome = SimulationEngine(**engine_arguments).run()
            if outcome["action"] != "restart":
                break
        connection.send(("finished", outcome))
    except Exception as error:
        connection.send(("error", str(error)))


def run_simulation_window(language="en", **engine_arguments):
    """Blocks until the simulation window is closed and returns the
    outcome of the last run: {"action": ..., "result": ...}."""
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_run, args=(sender, language, engine_arguments))
    process.start()
    sender.close()

    try:
        status, payload = receiver.recv()
    except EOFError:
        raise RuntimeError("The simulation window closed unexpectedly.") from None
    finally:
        process.join()

    if status == "error":
        raise RuntimeError(payload)
    return payload
