"""Runs the simulation window in its own process.

The simulation window (pygame) and the main window (Tkinter) cannot share
a process: once a simulation window has been opened and closed, creating
new Tkinter input fields crashes the interpreter.
"""
import multiprocessing


def _run(connection, engine_arguments):
    from simulation.engine import SimulationEngine

    try:
        while True:
            outcome = SimulationEngine(**engine_arguments).run()
            if outcome["action"] != "restart":
                break
        connection.send(("finished", outcome))
    except Exception as error:
        connection.send(("error", str(error)))


def run_simulation_window(**engine_arguments):
    """Blocks until the simulation window is closed and returns the
    outcome of the last run: {"action": ..., "result": ...}."""
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_run, args=(sender, engine_arguments))
    process.start()
    sender.close()

    try:
        status, payload = receiver.recv()
    except EOFError:
        raise RuntimeError("Simülasyon penceresi beklenmedik biçimde kapandı.") from None
    finally:
        process.join()

    if status == "error":
        raise RuntimeError(payload)
    return payload
