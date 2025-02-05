New-Item -ItemType Directory -Path build -Force
Set-Location build
cmake ..
cmake --build .
