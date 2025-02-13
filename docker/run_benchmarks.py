import argparse
import subprocess
import datetime
import os

import logging
logging.basicConfig(level = logging.INFO)

PRECOMPILERS=["none", "ppcg","pocc","pluto1","pluto2","pluto3"]
COMPILERS=["gcc", "icc", "rose", "polly", "polyopt"]

output_base_path = "/work/output_data/" + datetime.datetime.today().strftime("%Y%m%d-%H%M%S")
print(f"{output_base_path=}")

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench", default="all")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--precompiler", default='all', choices=["all"] + PRECOMPILERS, nargs="+")
    parser.add_argument("--compiler", default='all', choices=["all"] + COMPILERS, nargs="+")
    parser.add_argument("--compile-only", default=True, action='store_false', dest="run", help="Do not run, compile only")
    return parser.parse_args()

def get_bench_path(spec):
    base_path = "/usr/local/polyhedral/polybench"

    paths = {
        "linear-algebra/kernels": ["2mm", "3mm", "atax", "bicg", "doitgen", "mvt"],
        "linear-algebra/blas": ["gemm", "gemver", "gesummv", "symm", "syr2k", "syrk", "trmm"],
        "linear-algebra/solvers": ["cholesky", "durbin", "gramschmidt", "lu", "ludcmp", "trisolv"],
        "datamining": ["correlation", "covariance"],
        "medley": ["deriche", "nussinov", "floyd-warshall"],
        "stencils": ["adi", "jacobi-1d", "fdtd-2d", "jacobi-2d", "heat-3d", "seidel-2d"],
    }

    selected = []
    for sub_path, benchmarks in paths.items():
        components = sub_path.split("/")
        if spec in benchmarks:
            selected.append((base_path, sub_path, spec))
        if spec in components or spec == "all" :
            selected += [ (base_path, sub_path, b) for b in benchmarks ]

    logging.info("Selected benchmarks: %s", " ".join(name for _,_,name in selected))

    return selected


def cmd(command, stdout = None, stderr=None, phase = None):
    if phase is None:
        phase = datetime.datetime.today().strftime("%Y%m%d-%H%M%S")
    if stdout is None:
        stdout = f"output_{phase}.log"
    if stderr is None:
        stderr = f"error_{phase}.log"

    try:
        with open(stdout, "w") as output, open(stdout, "w") as error:
            command_str = " ".join(command)
            subprocess.check_call(command_str, shell=True, stdout=output, stderr=error, timeout=10*60)
    except subprocess.CalledProcessError as e:
        logging.warning(f"Command: \"{command_str}\" failed")




def run_benchmark(paths, precompilers, compilers, run=True, debug=False):
    base_path, sub_path, bench = paths

    include_args = [ "-I", f"{base_path}/utilities", "-I", f"{base_path}/{sub_path}/{bench}" ]
    restrict_args = [ "-DPOLYBENCH_USE_RESTRICT", "-fopenmp" ]

    common_args  = [ "-DPOLYBENCH_TIME", "-DMINI_DATASET", "-DPOLYBENCH_USE_SCALAR_LB", "-DPOLYBENCH_USE_C99_PROTO", ]
    common_args += [ "-O3", "-march=native" ]
    common_args += [ f"{base_path}/utilities/polybench.c", f"{bench}.*.c" , "-o", f"{bench}_time", "-lm" ]
    common_args += include_args
    compile_commands = {
        "gcc":       [ "graphite-gcc", "-ffast-math" ] + common_args + restrict_args,
        "icc":       [ "icc", "-fp-model=fast" ] + common_args + restrict_args,
        "rose":      [ "rose-compiler", "-ffast-math" ] + common_args,
        "polly":     [ "polly-clang", "-ffast-math" ] + common_args + restrict_args,
        "polyopt":   [ "polyopt", "--polyopt-scalar-privatization --polyopt-safe-math-func" ] + common_args,
        "polygeist": [ "polygeist", "-ffast-math" ] + common_args,
    }

    bench_c = f"{base_path}/{sub_path}/{bench}/{bench}.c"
    precompile_commands = {
        "none":   [ "cp", bench_c, f"{bench}.none.c" ],
        "ppcg":   [ "ppcg", "--tile", "--target=c", "--openmp", bench_c ] + include_args,
        "pluto1": [ "polycc", "--tile", "--parallel", "--smartfuse", "--prevector", bench_c ],
        "pluto2": [ "polycc", "--l2tile", "--parallel", "--smartfuse", "--prevector", bench_c ],
        "pluto3": [ "polycc", "--diamond-tile", "--parallel", "--smartfuse", "--prevector", bench_c ],
        "pocc":   [ "pocc", "--pluto-tile", "--pluto-parallel", "--pragmatizer", "--vectorizer", "--pluto-scalpriv", "--pluto-fuse smartfuse", "--output", f"{bench}.pocc.c", bench_c ],
    }

    for precompiler in precompilers:
        for compiler in compilers:
            rundir = output_base_path + f"/{bench}/{precompiler}/{compiler}"
            os.makedirs(rundir)
            os.chdir(rundir)
            logging.info(f"{rundir=}")

            cmd(precompile_commands[precompiler], phase="precompile")
            cmd(compile_commands[compiler], phase="compile")
            logging.info(f"{rundir}: compile completed.")
            if run:
                cmd([ f"./{bench}_time", ], stderr=f"{bench}.err", stdout=f"{bench}.out", phase="run")
                with open(f"{bench}.out") as f: time = f.read().strip()
                logging.info(f"{rundir}: run completed - took {time}.")

if __name__ == "__main__":
    args = parse_arguments()

    paths = get_bench_path(args.bench)

    if 'all' in args.compiler: args.compiler = COMPILERS
    print("Selected compilers: ", args.compiler)

    if 'all' in args.precompiler: args.precompiler = PRECOMPILERS
    print("Selected pre-compilers: ", args.precompiler)


    for p in paths:
        run_benchmark(p, args.precompiler, args.compiler, args.run, args.debug)
