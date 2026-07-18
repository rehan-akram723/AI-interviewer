#!/bin/bash
echo "Running Backend Tests..."
cd backend
../env/bin/python -m pytest "$@"
