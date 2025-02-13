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


def cmd(command, phase = None):
    if phase is None:
        phase = datetime.datetime.today().strftime("%Y%m%d-%H%M%S")

    try:
        with open(f"output_{phase}.log", "w") as output:
            subprocess.check_call(command, shell=True, stdout=output, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(f"Command: \"{command}\" failed")




def run_benchmark(paths, precompilers, compilers, run=True, debug=False):
    base_path, sub_path, bench = paths

    include_args = f" -I {base_path}/utilities -I {base_path}/{sub_path}/{bench} "
    restrict_args = " -DPOLYBENCH_USE_RESTRICT -fopenmp "

    common_args  = f"-DPOLYBENCH_TIME -DEXTRALARGE_DATASET -DPOLYBENCH_DUMP_ARRAYS -DPOLYBENCH_USE_SCALAR_LB -DPOLYBENCH_USE_C99_PROTO "
    common_args += f"-O3 -march=native "
    common_args += f"{base_path}/utilities/polybench.c {bench}.*.c -o {bench}_time -lm "
    common_args += include_args
    compile_commands = {
        "gcc":   "graphite-gcc -ffast-math " + common_args + restrict_args,
        "icc":   "icc -fp-model=fast " + common_args + restrict_args,
        "rose":  "rose-compiler -ffast-math "  + common_args,
        "polly": "polly-clang -ffast-math " + common_args + restrict_args,
        "polyopt": "polyopt --polyopt-scalar-privatization --polyopt-safe-math-func " + common_args,
        "polygeist": "polygeist -ffast-math " + common_args,
    }

    precompile_commands = {
        "none": f"cp {base_path}/{sub_path}/{bench}/{bench}.c {bench}.none.c",
        "ppcg": f"ppcg --tile --target=c --openmp {base_path}/{sub_path}/{bench}/{bench}.c " + include_args,
        "pluto1": f"polycc --tile  --parallel --smartfuse --prevector {base_path}/{sub_path}/{bench}/{bench}.c ",
        "pluto2": f"polycc --l2tile  --parallel --smartfuse --prevector {base_path}/{sub_path}/{bench}/{bench}.c ",
        "pluto3": f"polycc --diamond-tile  --parallel --smartfuse --prevector {base_path}/{sub_path}/{bench}/{bench}.c ",
        "pocc": f"pocc --pluto-tile --pluto-parallel --pragmatizer --vectorizer --pluto-scalpriv --pluto-fuse smartfuse --output {bench}.pocc.c {base_path}/{sub_path}/{bench}/{bench}.c ",
    }

    for precompiler in precompilers:
        for compiler in compilers:
            rundir = output_base_path + f"/{bench}/{precompiler}/{compiler}"
            os.makedirs(rundir)
            os.chdir(rundir)
            print(f"{rundir=}")

            cmd(precompile_commands[precompiler])
            cmd(compile_commands[compiler])
            print(f"{rundir}: compile completed.")
            if run:
                cmd(f"./{bench}_time 2> ./{bench}_{compiler}.out")
                print(f"{rundir}: run completed.")

if __name__ == "__main__":
    args = parse_arguments()

    paths = get_bench_path(args.bench)

    if 'all' in args.compiler: args.compiler = COMPILERS
    print("Selected compilers: ", args.compiler)

    if 'all' in args.precompiler: args.precompiler = PRECOMPILERS
    print("Selected pre-compilers: ", args.precompiler)


    for p in paths:
        run_benchmark(p, args.precompiler, args.compiler, args.run, args.debug)
