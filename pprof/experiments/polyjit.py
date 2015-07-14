#!/usr/bin/env python
# encoding: utf-8
"""
The 'polyjit' experiment.

This experiment uses likwid to measure the performance of all binaries
when running with polyjit support enabled.
"""
from pprof.experiment import step, substep, RuntimeExperiment
from pprof.experiment import compilestats
from pprof.settings import config
from pprof.utils.schema import CompileStat

from plumbum import local
from os import path


class PolyJIT(RuntimeExperiment):

    """The polyjit experiment."""

    def run_step_compilestats(self, p):
        """ Compile the project and track the compilestats. """
        llvm_libs = path.join(config["llvmdir"], "lib")

        with step("Track Compilestats @ -O3"):
            p.clean()
            p.prepare()
            p.download()
            with substep("Configure Project"):

                def track_compilestats(cc, **kwargs):
                    from pprof.utils.db import persist_compilestats
                    from pprof.utils.run import handle_stdin
                    new_cc = handle_stdin(cc["-mllvm", "-stats"], kwargs)

                    retcode, stdout, stderr = new_cc.run()
                    if retcode == 0:
                        stats = []
                        for stat in compilestats.get_compilestats(stderr):
                            c = CompileStat()
                            c.name = stat["desc"].rstrip()
                            c.component = stat["component"].rstrip()
                            c.value = stat["value"]
                            stats.append(c)
                        persist_compilestats(run, session, stats)

                p.compiler_extension = track_compilestats
                p.configure()
            with substep("Build Project"):
                p.build()

    def run_step_jit(self, p):
        """Run the experiment without likwid."""
        with step("JIT, no instrumentation"):
            p.clean()
            p.prepare()
            p.download()
            with substep("Build"):
                p.configure()
                p.build()
            with substep("Execute {}".format(p.name)):
                def run_with_time(run_f, args, **kwargs):
                    from pprof.utils.db import persist_time
                    from plumbum.cmd import time
                    from pprof.utils.run import fetch_time_output, handle_stdin

                    project_name = kwargs.get("project_name", p.name)
                    timing_tag = "PPROF-JIT: "

                    run_cmd = time["-f", timing_tag + "%U-%S-%e", run_f]
                    run_cmd = handle_stdin(run_cmd[args], kwargs)
                    _, _, stderr = run_cmd.run()

                    timings = fetch_time_output(timing_tag,
                                                timing_tag + "{:g}-{:g}-{:g}",
                                                stderr.split("\n"))
                    if len(timings) == 0:
                        return

                    persist_time(run, session, timings)
                p.run(run_with_time)

    def run_step_likwid(self, p):
        """Run the experiment with likwid."""
        with step("JIT, likwid"):
            p.clean()
            p.prepare()
            p.download()
            p.cflags = ["-DLIKWID_PERFMON"] + p.cflags

            with substep("Build"):
                p.configure()
                p.build()
            with substep("Execute {}".format(p.name)):
                from pprof.settings import config

                def run_with_likwid(run_f, args, **kwargs):
                    from pprof.utils.db import persist_likwid
                    from pprof.likwid import get_likwid_perfctr
                    from plumbum.cmd import rm

                    project_name = kwargs.get("project_name", p.name)
                    likwid_f = p.name + ".txt"

                    for group in ["CLOCK"]:
                        likwid_path = path.join(config["likwiddir"], "bin")
                        likwid_perfctr = local[
                            path.join(likwid_path, "likwid-perfctr")]
                        for i in range(int(config["jobs"])):
                            run_cmd = \
                                likwid_perfctr["-O", "-o", likwid_f, "-m",
                                               "-C", "0-{:d}".format(i),
                                               "-g", group, run_f]

                            run_cmd = handle_stdin(run_cmd[args], kwargs)
                            run_cmd()

                            likwid_measurement = get_likwid_perfctr(likwid_f)
                            """ Use the project_name from the binary, because we
                                might encounter dynamically generated projects.
                            """
                            persist_likwid(run, session, likwid_measurement)
                            rm("-f", likwid_f)
                p.run(run_with_likwid)

    def run_project(self, p):
        """
        Execute the pprof experiment.

        We perform this experiment in 2 steps:
            1. with likwid disabled.
            2. with likwid enabled.
        """
        p.ldflags = ["-lpjit", "-lgomp"]

        ld_lib_path = filter(None, config["ld_library_path"].split(":"))
        p.ldflags = ["-L" + el for el in ld_lib_path] + p.ldflags
        p.cflags = ["-Rpass=\"polyjit*\"",
                    "-Xclang", "-load",
                    "-Xclang", "LLVMPolyJIT.so",
                    "-O3",
                    "-mllvm", "-jitable",
                    "-mllvm", "-polly-delinearize=false",
                    "-mllvm", "-polly-detect-keep-going",
                    "-mllvm", "-polli"]
        with local.env(PPROF_ENABLE=0):
            self.run_step_likwid(p)
            self.run_step_jit(p)
            self.run_step_compilestats(p)
