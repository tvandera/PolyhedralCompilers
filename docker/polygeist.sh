#!/bin/bash

set -e
set -o pipefail

FLAGS=()
INPUTS=()
OBJECTS=()
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -o)
      OUTPUT="$2"
      shift # past argument
      shift # past value
      ;;
    *.c)
      INPUTS+=("$1")
      shift # past argument
      ;;
    *)
      FLAGS+=("$1")
      shift # past flag
      ;;
  esac
done

[ -z $OUTPUT ] && OUTPUT="a.out"

echo "FLAGS = ${FLAGS[@]}"
echo "OUTPUT = $OUTPUT"

export PATH=/usr/local/polyhedral/polygeist/bin:/usr/local/polyhedral/polygeist/bin:$PATH

for INPUT in ${INPUTS[@]}
do
  /usr/local/polyhedral/polygeist/bin/mlir-clang \
    ${FLAGS[@]} "$INPUT" -o "$INPUT".mlir

  /usr/local/polyhedral/polymer/bin/polymer-opt \
      --demote-loop-reduction \
      --extract-scop-stmt \
      --pluto-opt='parallelize=1' \
      --inline \
      --canonicalize \
      "$INPUT".mlir \
      -o "$INPUT".popt

  /usr/local/polyhedral/polygeist/bin/mlir-opt \
      -mem2reg \
      -detect-reduction \
      -mem2reg \
      -canonicalize \
      -affine-parallelize \
      -lower-affine \
      -convert-scf-to-openmp \
      -convert-scf-to-std \
      -convert-openmp-to-llvm \
      -o "$INPUT".opt \
      "$INPUT".mlir

  /usr/local/polyhedral/polygeist/bin/mlir-translate \
      -mlir-to-llvmir \
      -o "$INPUT".ll \
      "$INPUT".opt

  /usr/local/polyhedral/polygeist/bin/clang -c -o "$INPUT".o "$INPUT".ll

  OBJECTS+=("$INPUT".o)

done

/usr/bin/clang -fopenmp -lm -o "$OUTPUT" ${OBJECTS[@]}