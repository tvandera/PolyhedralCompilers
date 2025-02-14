#!/bin/bash
# copies $exe and dynamic library deps to $prefix

set -e

exe="$1"
prefix="$2"

# copies $fullpath to $prefix/lib, or $prefix/bin
# updates rpath to point to ../lib
function to_prefix {
    prefix="$1"
    fullpath="$2"
    filename=$(basename "$fullpath")

    if file -L $fullpath | grep -q executable; then
        dest="$prefix"/bin/"$filename"
    elif file -L $fullpath | grep -q "shared object"; then
        dest="$prefix"/lib/"$filename"
    else
        echo "Unknown file type: $fullpath"
        exit -1
    fi

    mkdir -p "$dest"
    cp "$fullpath" "$dest"
    patchelf --set-rpath '$ORIGIN/../lib' "$dest"
}

# copies $bin to $prefix
# does the same for dynamic library deps
# updates rpath to point to ../lib
copy_libs() {
    local bin="$1"
    ldd "$bin" | awk '{print $3}' | grep -v '^$' | while read -r lib; do
        if [[ $lib == "not" ]]; then
            ldd $bin
            echo "Not found!" >&2
            exit -1
        fi

        if [[ -f "$lib" ]] && [[ ! $lib == /lib* ]] && [[ ! $lib == /usr/lib* ]] ; then
            to_prefix "$lib" "$prefix"
            copy_libs "$lib"  # Recursively check dependencies of the library
        fi
    done
}

copy_libs "$exe"
