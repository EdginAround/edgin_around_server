#!/bin/sh

function usage() {
    echo 'Commands:'
    echo ' - mypy - runs mypy checker in the main app'
    echo ' - black - runs `black` code formatter'
    echo ' - tests - runs unit tests'
}

function run_mypy() {
    python -m mypy edgin_around_server.py --show-error-codes $@
}

function run_mypy_tests() {
    python -m mypy test/test_*.py --show-error-codes $@
}

function run_black() {
    python -m black . --config black.toml
}

function run_tests() {
    python -m unittest $@
}

if (( $# > 0 )); then
    command=$1
    shift

    case $command in
        'mypy')
            run_mypy $@
            ;;
        'black')
            run_black $@
            ;;
        'tests')
            run_mypy && run_mypy_tests && run_tests $@
            ;;
        *)
            echo "Command \"$command\" unknown."
            echo
            usage
            ;;
    esac
else
    echo 'Please give a command.'
    echo
    usage
fi

