@echo off
echo Running Backend Tests...
cd backend
..\env\Scripts\python -m pytest %*
