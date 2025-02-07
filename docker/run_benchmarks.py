import argparse
import subprocess

import logging
logging.basicConfig(level = logging.INFO)

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench", default="all")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--compiler", default='gcc', choices=["gcc", "clang", "icc", "rose", "polly", "graph", "polyopt"], nargs="+")
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


def cmd(c):
    print("Executing: ", c)
    subprocess.check_call(c, shell=True)

def run_benchmark(paths, compilers, debug):
    base_path, sub_path, bench = paths

    restrict = "-DPOLYBENCH_USE_RESTRICT -fopenmp"
    common_args  = f"-DPOLYBENCH_TIME -DEXTRALARGE_DATASET -DPOLYBENCH_DUMP_ARRAYS -DPOLYBENCH_USE_SCALAR_LB -DPOLYBENCH_USE_C99_PROTO "
    common_args += f"-O3 -march=native "
    common_args += f"-I {base_path}/utilities -I {base_path}/{sub_path}/{bench} "
    common_args += f"{base_path}/utilities/polybench.c {base_path}/{sub_path}/{bench}/{bench}.c -o {bench}_time -lm"
    compile_commands = {
        "gcc":   "graphite-gcc -ffast-math " + common_args + restrict,
        "clang": "polly-clang -ffast-math " + common_args + restrict,
        "icc":   "icc -fp-model=fast " + common_args + restrict,
        "rose":  "rose-compiler -ffast-math "  + common_args,
        "polyopt": "polyopt --polyopt-scalar-privatization --polyopt-safe-math-func " + common_args,
    }

    for compiler in compilers:
        cmd(compile_commands[compiler])
        cmd(f"./{bench}_time 2> ./output_data/{bench}_{compiler}.out")
        print(f"{compiler} run completed.")

if __name__ == "__main__":
    args = parse_arguments()
    paths = get_bench_path(args.bench)

    for p in paths:
        run_benchmark(p, args.compiler, args.debug)
