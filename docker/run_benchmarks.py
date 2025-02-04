import os
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench", default="all")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--compiler", choices=["gcc", "clang", "icc", "rose", "polly", "graph", "polyopt"], nargs="+")
    return parser.parse_args()

def get_bench_path(bench):
    paths = {
        "linear-algebra/kernels": ["2mm", "3mm", "atax", "bicg", "doitgen", "mvt"],
        "linear-algebra/blas": ["gemm", "gemver", "gesummv", "symm", "syr2k", "syrk", "trmm"],
        "linear-algebra/solvers": ["cholesky", "durbin", "gramschmidt", "lu", "ludcmp", "trisolv"],
        "datamining": ["correlation", "covariance"],
        "medley": ["deriche", "nussinov", "floyd-warshall"],
        "stencils": ["adi", "jacobi-1d", "fdtd-2d", "jacobi-2d", "heat-3d", "seidel-2d"],
    }
    for path, benchmarks in paths.items():
        if bench in benchmarks:
            return path
    return None

def run_benchmark(bench, bench_path, compilers, debug):
    if debug:
        print(f"Running benchmark: {bench}")

    common_args = f"-O3 -fopenmp -march=native -I utilities -I {bench_path}/{bench} utilities/polybench.c {bench_path}/{bench}/{bench}.c -o {bench}_time -lm"
    compile_commands = {
        "gcc":   "graphite-gcc -ffast-math" + common_args,
        "clang": "polly-clang -ffast-math" + common_args,
        "icc":   "icc -fp-model=fast" + common_args,
    }

    for compiler in compilers:
        if compiler in compile_commands:
            os.system(compile_commands[compiler])
            os.system(f"./{bench}_time 2> ./output_data/{bench}_{compiler}.out")
            os.remove(f"./{bench}_time")
            print(f"{compiler} run completed.")

if __name__ == "__main__":
    args = parse_arguments()
    bench_path = get_bench_path(args.bench)

    if not bench_path:
        print("Invalid benchmark specified.")
    else:
        run_benchmark(args.bench, bench_path, args.compiler, args.debug)
